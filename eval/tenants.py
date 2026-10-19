"""Per-institution graphs: many tenants on one FalkorDB, each its own graph.

Loads TENANTS independently seeded datasets into graphs corridor_<tenant>, times the evidence
tools per tenant, and checks isolation through the API's X-Tenant header.
Run: PYTHONPATH=api .venv/bin/python eval/tenants.py 100   (pip install falkordblite)
"""
import json, os, statistics, sys, tempfile, time
from pathlib import Path
from data.generate import generate
from data.load import load
from agent.tools import CorridorTools, query_records

ROOT = Path(__file__).resolve().parents[1]
TENANTS = int(sys.argv[1]) if len(sys.argv) > 1 else 100


def main():
    from redislite.falkordb_client import FalkorDB
    from fastapi.testclient import TestClient
    db = FalkorDB(tempfile.mkdtemp() + '/tenants.db')
    def graph(name):
        g = db.select_graph(name)
        g.client.list_graphs = db.list_graphs
        return g
    names = [f't{i:03d}' for i in range(TENANTS)]
    t = time.perf_counter()
    for i, name in enumerate(names):
        load(graph(f'corridor_{name}'), generate(100 + i)[0], batch_size=2000)
    load_s = round(time.perf_counter() - t, 1)
    info = db.execute_command('INFO', 'memory')
    used = info['used_memory'] if isinstance(info, dict) else int(str(info).split('used_memory:')[1].split()[0])
    sample = names[:: max(1, TENANTS // 20)]
    ms = {'fan_in': [], 'circular_flows': [], 'shared_identifiers': []}
    for name in sample:
        tools = CorridorTools(graph(f'corridor_{name}'))
        latest = query_records(tools.graph, 'account_context', {'account_id': 'collector_0'})[0]['latest_transfer_ts']
        for key, call in (('fan_in', lambda: tools.fan_in('collector_0', latest - 172800, 500)),
                          ('circular_flows', lambda: tools.circular_flows('cycle_0', 5)),
                          ('shared_identifiers', lambda: tools.shared_identifiers('shared_0'))):
            for _ in range(3):
                s = time.perf_counter(); call(); ms[key].append((time.perf_counter() - s) * 1000)
    # Isolation through the API: a case opened in tenant A must not appear in tenant B.
    os.environ['CORRIDOR_TENANTS'] = ','.join(names)
    os.environ['GRAPH_NAME'] = 'corridor'
    from main import create_app
    a, b = names[0], names[1]
    case_id = CorridorTools(graph(f'corridor_{a}')).open_case('collector_0')['case_id']
    with TestClient(create_app(graph_factory=lambda graph_name=None: graph(graph_name or 'corridor'))) as client:
        hist_a = client.get('/accounts/collector_0/history', headers={'X-Tenant': a}).json()['cases']
        hist_b = client.get('/accounts/collector_0/history', headers={'X-Tenant': b}).json()['cases']
        unknown = client.get('/flags', headers={'X-Tenant': 'not_a_tenant'}).status_code
    out = {'tenants': TENANTS, 'graphs_on_one_server': len([n for n in db.list_graphs() if str(n).startswith('corridor_t')]),
           'load_seconds': load_s, 'used_memory_mb': round(used / 2**20, 1),
           'memory_per_tenant_mb': round(used / 2**20 / TENANTS, 2), 'sampled_tenants': len(sample),
           'median_ms': {k: round(statistics.median(v), 2) for k, v in ms.items()},
           'p95_ms': {k: round(sorted(v)[int(len(v) * .95) - 1], 2) for k, v in ms.items()},
           'isolation': {'case_in_tenant_a': case_id in [c['case_id'] for c in hist_a],
                         'case_visible_in_tenant_b': case_id in [c['case_id'] for c in hist_b],
                         'unknown_tenant_status': unknown},
           'engine': 'falkordblite (embedded FalkorDB 4.18), single laptop process'}
    (ROOT / 'eval/tenants.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
