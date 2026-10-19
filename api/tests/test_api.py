"""M5 HTTP/SSE integration tests, real isolated graph and scripted model."""
import json
import os
import threading
import unittest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from agent.model import ModelError
from agent.tools import query_records
from data.generate import generate
from data.load import load
from db import connect, DatabaseError
from main import create_app
from tests.test_agent import ScriptedModel


def events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]


class APIErrorTests(unittest.TestCase):
    def test_database_error_is_redacted(self):
        def unavailable(): raise DatabaseError('secret host password')
        with TestClient(create_app(graph_factory=unavailable)) as client:
            response = client.get('/flags')
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('secret', response.text)

    def test_approval_is_disabled_without_operator_secret(self):
        def forbidden(): self.fail('Unauthorized approval must not access graph')
        with patch.dict(os.environ,{'CORRIDOR_APPROVAL_TOKEN':''}), TestClient(create_app(graph_factory=forbidden)) as client:
            response=client.post('/cases/a/approve-freeze',json={'plan_id':'p','confirm_simulated_freeze':True})
            self.assertEqual(response.status_code,403)

    def test_model_preflight_creates_no_case(self):
        def unavailable(): raise ModelError('secret API key')
        def forbidden(): self.fail('Database accessed before model preflight')
        with TestClient(create_app(graph_factory=forbidden, model_factory=unavailable)) as client:
            response = client.post('/investigate/cycle_0', json={})
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('secret', response.text)
            self.assertEqual(client.post('/investigate/a', json={'corridor':'bad'}).status_code, 422)
            self.assertEqual(client.post('/admin/reset', json={'confirm_graph':'corridor'}).status_code, 403)


@unittest.skipUnless(os.getenv('CORRIDOR_LIVE_TESTS') == '1', 'Requires remote FalkorDB')
class APIGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old = os.environ.get('GRAPH_NAME')
        os.environ['GRAPH_NAME'] = 'corridor_test_' + uuid.uuid4().hex
        try: cls.graph = connect()
        finally:
            if old is None: os.environ.pop('GRAPH_NAME', None)
            else: os.environ['GRAPH_NAME'] = old
        cls.addClassCleanup(cls.graph.delete)
        data, _ = generate(42)
        load(cls.graph, data)

    def app(self, model_factory=ScriptedModel):
        return create_app(lambda: self.graph, model_factory)

    def test_queue_and_not_found(self):
        with TestClient(self.app()) as client:
            response = client.get('/flags')
            self.assertEqual(response.status_code, 200, response.text)
            flags = response.json()['flags']
            self.assertEqual({r['account_id'] for r in flags}, {r['account_id'] for r in generate(42)[1]['evaluation_flags']})
            self.assertTrue(all(r['corridor'] == 'US-NG' for r in flags))
            for path in ['/cases/missing', '/cases/missing/subgraph', '/cases/missing/stream']:
                self.assertEqual(client.get(path).status_code, 404)
            self.assertEqual(client.get('/accounts/missing/history').json(), {'cases': []})

    def test_investigate_stream_reconnect_and_saved_subgraph(self):
        with TestClient(self.app()) as client:
            response = client.post('/investigate/cycle_0', json={})
            self.assertEqual(response.status_code, 202, response.text)
            cid = response.json()['case_id']
            stream = client.get(f'/cases/{cid}/stream')
            self.assertIn('text/event-stream', stream.headers['content-type'])
            emitted = events(stream)
            self.assertEqual(emitted[0]['type'], 'opened')
            self.assertEqual(emitted[-2]['type'], 'closed')
            self.assertEqual(emitted[-1]['type'], 'end')
            resumed = events(client.get(f'/cases/{cid}/stream', headers={'Last-Event-ID': '1'}))
            self.assertEqual(resumed, emitted[1:])
            saved = client.get(f'/cases/{cid}').json()
            self.assertEqual(saved['case']['status'], 'closed')
            self.assertEqual(saved['routing']['decision_id'], 'DEC-6')
            self.assertEqual(len(saved['routing']['members']), len({m['id'] for m in saved['routing']['members']}))
            self.assertEqual(next(m['role'] for m in saved['routing']['members'] if m['id']=='cycle_0'), 'flagged')
            grounding = saved['grounding'][0]
            self.assertEqual(grounding['policy']['id'], 'POL-AML-1')
            self.assertEqual(grounding['source']['id'], 'DOC-1')
            self.assertEqual(grounding['author']['id'], 'emp_6')
            self.assertEqual(grounding['assignee']['id'], 'emp_0')
            self.assertEqual(grounding['team']['id'], 'team_0')
            for finding in saved['evidence']:
                self.assertEqual(len(finding['cited']), len(set(finding['cited'])))
                if finding['tool'] == 'guardrail':
                    self.assertIsNone(finding['query_text'])
                else:
                    self.assertTrue(finding['query_text'])
            graph = client.get(f'/cases/{cid}/subgraph').json()
            self.assertEqual(graph, saved['subgraph'])
            ids = {n['id'] for n in graph['nodes']}
            self.assertIn('cycle_0', ids)
            self.assertTrue(graph['edges'])
            self.assertTrue(all(e['source'] in ids and e['target'] in ids for e in graph['edges']))
            self.assertTrue(any(c['case_id'] == cid for c in client.get('/accounts/cycle_0/history').json()['cases']))
            self.assertEqual(client.get(f'/cases/{cid}/stream', headers={'Last-Event-ID':'bad'}).status_code, 422)
        with TestClient(self.app()) as restarted:
            snapshot = events(restarted.get(f'/cases/{cid}/stream'))
            self.assertEqual([e['type'] for e in snapshot], ['snapshot','end'])
            self.assertEqual(snapshot[0]['case']['status'], 'closed')

    def test_duplicate_start_and_reset_blocked_during_work(self):
        release = threading.Event()
        class SlowModel(ScriptedModel):
            def choose(self, context, findings):
                release.wait(15)
                return {'name':'finish_investigation','params':{}}
        with patch.dict(os.environ, {'CORRIDOR_ADMIN_TOKEN':'test-only-token'}), TestClient(self.app(SlowModel)) as client:
            try:
                started = client.post('/investigate/shared_0', json={})
                self.assertEqual(started.status_code, 202)
                self.assertEqual(client.post('/investigate/shared_0', json={}).status_code, 409)
                reset = client.post('/admin/reset', json={'confirm_graph':self.graph.name}, headers={'X-Admin-Token':'test-only-token'})
                self.assertEqual(reset.status_code, 409)
            finally: release.set()
            self.assertEqual(events(client.get(started.json()['stream_url']))[-1]['type'], 'end')

    def test_unknown_account_stream_closes_with_error(self):
        with TestClient(self.app()) as client:
            started = client.post('/investigate/missing', json={}).json()
            emitted = events(client.get(started['stream_url']))
            closed = next(e for e in emitted if e['type']=='closed')
            self.assertEqual(closed['decision']['error'], 'unknown_account')

    def test_z_reset_requires_exact_graph_and_restores_seed(self):
        with patch.dict(os.environ, {'CORRIDOR_ADMIN_TOKEN':'test-only-token'}), TestClient(self.app()) as client:
            headers = {'X-Admin-Token':'test-only-token'}
            self.assertEqual(client.post('/admin/reset', json={'confirm_graph':self.graph.name}).status_code, 403)
            self.assertEqual(client.post('/admin/reset', json={'confirm_graph':'other'}, headers=headers).status_code, 409)
            response = client.post('/admin/reset', json={'confirm_graph':self.graph.name}, headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['seed'], 42)
            self.assertEqual(query_records(self.graph, 'count_nodes')[0]['count'], len(generate(42)[0]['nodes']))


class RuleCheckTests(unittest.TestCase):
    def test_rule_check_recomputes_freeze_preconditions(self):
        import json as _json
        from types import SimpleNamespace
        from main import rule_check
        findings = [
            {'id': 'f1', 'tool': 'shared_identifiers', 'result_json': _json.dumps([{'account': x} for x in ('a1', 'a2', 'a3')])},
            {'id': 'f2', 'tool': 'ajo_payout_pattern', 'result_json': _json.dumps([{'shared_devices': ['d'], 'first_round': 1, 'next_round': 2}])},
            {'id': 'f3', 'tool': 'collector_rank', 'result_json': _json.dumps([{'account': 'a0', 'score': .1}])},
            {'id': 'f4', 'tool': 'min_freeze_set', 'result_json': _json.dumps([{'freeze_ids': ['a0']}])},
        ]
        graph = SimpleNamespace(ro_query=lambda q, p: SimpleNamespace(header=[(0, 'case'), (0, 'findings')], result_set=[[{}, findings]]))
        evidence = [{'finding_id': 'f1', 'cited': ['a0', 'a1', 'dev']}, {'finding_id': 'f2', 'cited': ['a0']},
                    {'finding_id': 'f3', 'cited': ['a0']}, {'finding_id': 'f4', 'cited': ['a0']}]
        check = rule_check(graph, 'case_x', evidence, ['a0', 'a1'])
        self.assertEqual(check['supports'], {'a0': ['ajo_payout_pattern', 'shared_identifiers'], 'a1': ['shared_identifiers']})
        self.assertEqual(check['corroborated_accounts'], ['a0'])
        self.assertTrue(check['freeze_allowed'])
        check = rule_check(graph, 'case_x', evidence[:1], ['a0', 'a1'])
        self.assertFalse(check['freeze_allowed'])
