"""Fixed query registry. No runtime Cypher construction."""
from pathlib import Path
from db import DatabaseError

QUERY_DIR = Path(__file__).resolve().parents[1] / 'queries'
QUERIES = {p.stem: p.read_text() for p in QUERY_DIR.glob('*.cypher')}


def run_query(graph, name, params=None, *, readonly=False):
    if name not in QUERIES:
        raise ValueError(f'Unknown query: {name}')
    try:
        method = graph.ro_query if readonly else graph.query
        return method(QUERIES[name], params or {}).result_set
    except Exception:
        raise DatabaseError(f'FalkorDB query {name} failed; check connectivity and server compatibility.') from None


READ_TOOLS = frozenset(('shared_identifiers', 'circular_flows', 'fan_in',
    'ajo_payout_pattern', 'ring_communities', 'connected_cluster', 'collector_rank',
    'link_to_known_bad', 'corridor_context', 'precedents', 'who_knows', 'prior_cases'))
TOOL_NAMES = READ_TOOLS | {'open_case', 'record_finding', 'close_case'}


def query_records(graph, name, params=None, *, readonly=True):
    """Run a named fixed query and return JSON-compatible records with column names."""
    if name not in QUERIES:
        raise ValueError(f'Unknown query: {name}')
    try:
        result = (graph.ro_query if readonly else graph.query)(QUERIES[name], params or {})
        columns = [column[1] for column in result.header]
        return [dict(zip(columns, row)) for row in result.result_set]
    except Exception:
        raise DatabaseError(f'FalkorDB query {name} failed; check connectivity and server compatibility.') from None


def _id(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError('Identifiers must be nonempty strings of at most 256 characters.')
    return value


def _ids(values):
    if not isinstance(values, list) or len(values) > 200:
        raise ValueError('Supply a list of at most 200 identifiers.')
    return list(dict.fromkeys(_id(value) for value in values))


class CorridorTools:
    """Fixed M2 tools. These write receipts, not model verdict guardrails."""
    def __init__(self, graph):
        self.graph = graph

    def call(self, name, **params):
        if name not in TOOL_NAMES:
            raise ValueError('Unknown tool.')
        return getattr(self, name)(**params)

    def _read(self, name, **params):
        return query_records(self.graph, name, params)

    def _write(self, name, **params):
        rows = query_records(self.graph, name, params, readonly=False)
        if not rows:
            raise ValueError('Write rejected: case state or referenced entities are invalid.')
        return rows[0]

    def shared_identifiers(self, account_id):
        return self._read('shared_identifiers', account_id=_id(account_id))

    def circular_flows(self, account_id, max_hops=5):
        if type(max_hops) is not int or not 2 <= max_hops <= 5:
            raise ValueError('max_hops must be an integer from 2 through 5.')
        rows = self._read('circular_flows', account_id=_id(account_id), max_hops=max_hops)
        return sorted(rows, key=lambda r: (len(r['transfers']), r['transfers']))[:10]

    def fan_in(self, account_id, since, max_amount):
        import math
        if type(since) is not int or since < 0:
            raise ValueError('since must be a nonnegative Unix timestamp in seconds.')
        if type(max_amount) not in (int, float) or not math.isfinite(max_amount) or max_amount <= 0:
            raise ValueError('max_amount must be positive and finite.')
        return self._read('fan_in', account_id=_id(account_id), since=since, max_amount=max_amount)

    def ajo_payout_pattern(self, pool_id):
        return self._read('ajo_payout_pattern', pool_id=_id(pool_id))

    def ring_communities(self, account_ids):
        ids = _ids(account_ids)
        return self._read('ring_communities', account_ids=ids) if ids else []

    def connected_cluster(self, account_id):
        return self._read('connected_cluster', account_id=_id(account_id))

    def collector_rank(self, account_ids):
        ids = _ids(account_ids)
        return self._read('collector_rank', account_ids=ids) if ids else []

    def link_to_known_bad(self, account_id):
        return self._read('link_to_known_bad', account_id=_id(account_id))

    def corridor_context(self, corridor_code):
        return self._read('corridor_context', corridor_code=_id(corridor_code))

    def precedents(self, policy_id):
        return self._read('precedents', policy_id=_id(policy_id))

    def who_knows(self, pattern):
        return self._read('who_knows', pattern=_id(pattern))

    def prior_cases(self, account_id, exclude_case_id=''):
        if not isinstance(exclude_case_id, str):
            raise ValueError('exclude_case_id must be a string.')
        return self._read('prior_cases', account_id=_id(account_id), exclude_case_id=exclude_case_id)

    def open_case(self, account_id):
        import time
        import uuid
        return self._write('open_case', account_id=_id(account_id),
                           case_id='case_'+uuid.uuid4().hex, now=int(time.time()))

    def record_finding(self, case_id, step, text, tool, params, cited_ids, *,
                       result=None, rejected_citations=None, interpretation_source="unspecified"):
        import json
        import time
        import uuid
        if tool not in READ_TOOLS:
            raise ValueError('A finding must identify a known investigation tool.')
        if type(step) is not int or step < 1:
            raise ValueError('step must be a positive integer.')
        if not isinstance(text, str) or not text.strip() or len(text)>10000:
            raise ValueError('Finding text must be nonempty and at most 10000 characters.')
        if not isinstance(params, dict):
            raise ValueError('params must be a JSON object.')
        cited = _ids(cited_ids)
        return self._write('record_finding' if cited else 'record_empty_finding',
            case_id=_id(case_id), finding_id='finding_'+uuid.uuid4().hex, step=step,
            text=text, tool=tool, query_name=tool,
            params=json.dumps(params, sort_keys=True, allow_nan=False), cited_ids=cited, now=int(time.time()),
            result_json=json.dumps(result, sort_keys=True, allow_nan=False),
            rejected_citations=json.dumps(rejected_citations or []), interpretation_source=interpretation_source)

    def close_case(self, case_id, verdict, risk, pattern, policy_id, decision_id, assignee_id, members, *,
                   rationale="", proposed_verdict="", guardrail_reasons=None, step_cap_reached=False):
        import math
        if verdict not in ('FREEZE', 'MONITOR', 'CLEAR'):
            raise ValueError('Unknown verdict.')
        if type(risk) not in (int, float) or not math.isfinite(risk) or not 0 <= risk <= 1:
            raise ValueError('risk must be finite and between zero and one.')
        if pattern not in ('circular_layering','fan_in_mule','shared_device','ajo_abuse','none'):
            raise ValueError('Unknown pattern.')
        ids = _ids(members)
        if not ids:
            raise ValueError('At least one known member is required for grounded closure.')
        import time
        return self._write('close_case', case_id=_id(case_id), verdict=verdict, risk=risk,
            pattern=pattern, policy_id=_id(policy_id), decision_id=_id(decision_id),
            assignee_id=_id(assignee_id), members=ids, now=int(time.time()), rationale=rationale,
            proposed_verdict=proposed_verdict or verdict, guardrail_reasons=guardrail_reasons or [],
            step_cap_reached=step_cap_reached)
