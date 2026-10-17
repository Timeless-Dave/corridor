"""Single-worker local demo API. All graph access uses the fixed query registry."""
import asyncio
from contextlib import asynccontextmanager
import hmac
import json
import os
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
from agent.loop import Investigation
from agent.model import OpenAIModel, ModelError
from agent.tools import CorridorTools, query_records, QUERIES, READ_TOOLS
from data.generate import generate
from data.load import load
from db import connect, DatabaseError


class StartRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    corridor: Literal['US-NG', 'NG-US'] = 'US-NG'


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    confirm_graph: str


def identifier(value):
    if not value.strip() or len(value) > 256:
        raise HTTPException(422, 'ID must contain 1–256 characters.')
    return value


def create_app(graph_factory=connect, model_factory=OpenAIModel):
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    jobs = {}
    lock = asyncio.Lock()
    resetting = False

    @asynccontextmanager
    async def lifespan(app):
        yield
        await asyncio.gather(*(j['task'] for j in jobs.values()), return_exceptions=True)

    app = FastAPI(title='Corridor', lifespan=lifespan)

    @app.exception_handler(DatabaseError)
    async def database_error(request, error):
        return JSONResponse(status_code=503, content={'detail': 'Database unavailable; retry or inspect the case.'})

    @app.exception_handler(ModelError)
    async def model_error(request, error):
        return JSONResponse(status_code=503, content={'detail': 'Model unavailable; check local configuration.'})

    def case(graph, case_id):
        rows = query_records(graph, 'investigation_audit', {'case_id': identifier(case_id)})
        if not rows: raise HTTPException(404, 'Case not found.')
        return rows[0]

    def subgraph(graph, case_id):
        nodes = query_records(graph, 'api_subgraph_nodes', {'case_id': case_id})
        edges = query_records(graph, 'api_subgraph_edges', {'ids': [n['id'] for n in nodes]}) if nodes else []
        return {'nodes': nodes, 'edges': edges, 'possibly_truncated': len(nodes) == 500 or len(edges) == 1000}

    @app.get('/flags')
    def flags():
        rows = query_records(graph_factory(), 'api_flags')
        # The seeded review queue is the US→NG demo corridor, including recipient accounts.
        return {'flags': [dict(r, corridor='US-NG') for r in rows]}

    @app.get('/accounts/{account_id}/history')
    def history(account_id: str):
        return {'cases': CorridorTools(graph_factory()).prior_cases(identifier(account_id))}

    @app.get('/cases/{case_id}/subgraph')
    def get_subgraph(case_id: str):
        graph = graph_factory()
        case(graph, case_id)
        return subgraph(graph, case_id)

    @app.get('/cases/{case_id}')
    def get_case(case_id: str):
        graph = graph_factory()
        result = case(graph, case_id)
        result['routing'] = query_records(graph, 'case_state', {'case_id': case_id})[0]
        # Normalize duplicate aggregate projections without rewriting case history.
        members = {}
        priority = {'flagged': 3, 'collector': 2, 'member': 1}
        for member in result['routing']['members']:
            key = member.get('id')
            if key and (key not in members or priority.get(member.get('role'), 0) > priority.get(members[key].get('role'), 0)):
                members[key] = member
        result['routing']['members'] = list(members.values())
        result['evidence'] = query_records(graph, 'case_evidence', {'case_id': case_id})
        for finding in result['evidence']:
            finding['cited'] = list(dict.fromkeys(finding['cited']))
            name = finding.get('query_name')
            finding['query_text'] = QUERIES.get(name) if name in READ_TOOLS else None
        result['grounding'] = query_records(graph, 'api_case_grounding', {'case_id': case_id})
        result['subgraph'] = subgraph(graph, case_id)
        return result

    async def execute(job, investigation, account_id, corridor):
        try:
            await asyncio.to_thread(investigation.run, account_id, corridor)
        except Exception:
            job['events'].append({'type': 'error', 'case_id': investigation.case_id,
                                  'text': 'Investigation interrupted; inspect persisted case before retrying.'})
        finally:
            job['done'] = True

    @app.post('/investigate/{account_id}', status_code=202)
    async def investigate(account_id: str, body: StartRequest = StartRequest()):
        identifier(account_id)
        async with lock:
            if resetting: raise HTTPException(409, 'Graph reset in progress.')
            if any(not j['done'] and j['account_id'] == account_id for j in jobs.values()):
                raise HTTPException(409, 'Account investigation already running.')
            if sum(not j['done'] for j in jobs.values()) >= 4:
                raise HTTPException(429, 'Investigation capacity reached.')
            model = model_factory()  # Preflight before creating a case.
            graph = graph_factory()
            job = {'events': [], 'done': False, 'account_id': account_id}
            event_loop = asyncio.get_running_loop()
            investigation = Investigation(graph, model,
                on_event=lambda e: event_loop.call_soon_threadsafe(job['events'].append, e))
            cid = await asyncio.to_thread(investigation.prepare, account_id)
            # Bound in-memory replay; older cases remain readable from the graph.
            for old in list(jobs):
                if len(jobs) < 100: break
                if jobs[old]['done']: del jobs[old]
            jobs[cid] = job
            job['task'] = asyncio.create_task(execute(job, investigation, account_id, body.corridor))
            return {'case_id': cid, 'stream_url': f'/cases/{cid}/stream'}

    @app.get('/cases/{case_id}/stream')
    async def stream(case_id: str, after: int = Query(0, ge=0), last_event_id: str | None = Header(None)):
        identifier(case_id)
        if last_event_id is not None:
            try: after = int(last_event_id)
            except ValueError: raise HTTPException(422, 'Last-Event-ID must be a nonnegative integer.')
            if after < 0: raise HTTPException(422, 'Last-Event-ID must be a nonnegative integer.')
        snapshot = await asyncio.to_thread(case, graph_factory(), case_id)
        job = jobs.get(case_id)
        if job and after > len(job['events']): raise HTTPException(422, 'Event cursor is ahead of this stream.')

        def frame(number, event):
            return f'id: {number}\nevent: {event["type"]}\ndata: {json.dumps(event, allow_nan=False)}\n\n'

        async def events():
            if job is None:
                # Restart/eviction: durable snapshot, not a claim of exact event replay.
                yield frame(after + 1, {'type': 'snapshot', 'case_id': case_id, **snapshot})
                yield frame(after + 2, {'type': 'end', 'case_id': case_id,
                                      'status': snapshot['case']['status'], 'live': False})
                return
            cursor = after
            ticks = 0
            while True:
                while cursor < len(job['events']):
                    event = job['events'][cursor]
                    cursor += 1
                    yield frame(cursor, event)
                if job['done']:
                    yield frame(cursor + 1, {'type': 'end', 'case_id': case_id, 'live': False})
                    return
                await asyncio.sleep(.2)
                ticks += 1
                if ticks % 50 == 0: yield ': heartbeat\n\n'

        return StreamingResponse(events(), media_type='text/event-stream',
                                 headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    @app.post('/admin/reset')
    async def reset(body: ResetRequest, x_admin_token: str = Header('')):
        nonlocal resetting
        expected = os.getenv('CORRIDOR_ADMIN_TOKEN', '')
        if not expected or not hmac.compare_digest(expected, x_admin_token):
            raise HTTPException(403, 'Admin reset disabled or unauthorized.')
        async with lock:
            if resetting or any(not j['done'] for j in jobs.values()):
                raise HTTPException(409, 'Wait for active investigations or reset to finish.')
            graph = graph_factory()
            if body.confirm_graph != graph.name: raise HTTPException(409, 'Configured graph confirmation does not match.')
            resetting = True
        try:
            data, _ = await asyncio.to_thread(generate, 42)
            counts = await asyncio.to_thread(load, graph, data, reset=True)
            jobs.clear()
            return {'graph': graph.name, 'seed': 42, 'counts': counts}
        finally:
            resetting = False

    return app


app = create_app()
