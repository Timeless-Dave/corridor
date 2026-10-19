"""Scale benchmark: Corridor's fixed tools and the exact freeze plan on a 20x graph.

Merges WORLDS independently seeded copies of the synthetic dataset (ids prefixed per world)
into one graph on an embedded FalkorDB (falkordblite), then times each real tool call.
Run: PYTHONPATH=api .venv/bin/python eval/scale.py   (pip install falkordblite)
"""
import json, statistics, sys, tempfile, time
from pathlib import Path
from data.generate import generate
from data.load import load
from agent.tools import CorridorTools, query_records
from agent.simulate import plan

ROOT = Path(__file__).resolve().parents[1]
WORLDS = int(sys.argv[1]) if len(sys.argv) > 1 else 20
ID_KEYS = ('id', 'fingerprint', 'number', 'code')


def world(w):
    data, _ = generate(42 + w)
    p = f'w{w}_'
    nodes = [{**n, 'key': p + n['key'], 'props': {k: (p + v if k in ID_KEYS and isinstance(v, str) else v) for k, v in n['props'].items()}}
             for n in data['nodes']]
    edges = [{**e, 'source': p + e['source'], 'target': p + e['target'],
              'props': {k: (p + v if k == 'id' and isinstance(v, str) else v) for k, v in e['props'].items()}} for e in data['edges']]
    return nodes, edges


def timed(fn, n=5):
    out, ms = None, []
    for _ in range(n):
        t = time.perf_counter(); out = fn(); ms.append((time.perf_counter() - t) * 1000)
    return out, round(statistics.median(ms), 1)


def main():
    from redislite.falkordb_client import FalkorDB
    db = FalkorDB(tempfile.mkdtemp() + '/scale.db')
    graph = db.select_graph('corridor_scale')
    graph.client.list_graphs = db.list_graphs  # embedded client lacks this helper; the loader uses it
    nodes, edges = [], []
    for w in range(WORLDS):
        n, e = world(w); nodes += n; edges += e
    t = time.perf_counter()
    # The loader indexes Account/Device/Phone/Case/Corridor/Policy; at 50x, Person and pool lookups need one too.
    for label in ('Person', 'AjoPool', 'Merchant', 'Team', 'Employee', 'Doc', 'Decision'):
        graph.query(f'CREATE INDEX FOR (n:{label}) ON (n.id)')
    load(graph, {'nodes': nodes, 'edges': edges}, reset=False, batch_size=1000)
    load_s = round(time.perf_counter() - t, 1)
    counts = {r[0]: r[1] for r in graph.query('MATCH (n) RETURN labels(n)[0], count(n)').result_set}
    sent = graph.query('MATCH ()-[r:SENT]->() RETURN count(r)').result_set[0][0]
    tools = CorridorTools(graph)
    target = f'w{WORLDS // 2}_'
    collector, cycle, shared, ajo = target + 'collector_0', target + 'cycle_0', target + 'shared_0', target + 'ajo_0'
    latest = query_records(graph, 'account_context', {'account_id': collector})[0]['latest_transfer_ts']
    bench = {}
    rows, bench['fan_in'] = timed(lambda: tools.fan_in(collector, latest - 172800, 500))
    fan_senders = max((r['senders'] for r in rows), default=0)
    rows, bench['circular_flows'] = timed(lambda: tools.circular_flows(cycle, 5))
    cycles = len(rows)
    rows, bench['shared_identifiers'] = timed(lambda: tools.shared_identifiers(shared))
    ring = [collector] + [target + f'mule_{i}' for i in range(12)]
    _, bench['collector_rank_pagerank'] = timed(lambda: tools.collector_rank(ring), n=3)
    _, bench['ring_communities_label_propagation'] = timed(lambda: tools.ring_communities(ring), n=3)
    case = tools.open_case(collector)['case_id']
    tools.record_finding(case, 1, 'Scale benchmark citation', 'fan_in', {'account_id': collector}, ring)
    t = time.perf_counter()
    result = plan(graph, case, ring)[0]
    bench['freeze_plan_graph_copy_greedy_and_measure'] = round((time.perf_counter() - t) * 1000, 1)
    out = {'worlds': WORLDS, 'accounts': counts.get('Account'), 'sent_transfers': sent, 'nodes_total': sum(counts.values()),
           'load_seconds': load_s, 'engine': 'falkordblite (embedded FalkorDB), single laptop process',
           'median_ms': bench, 'checks': {'fan_in_senders': fan_senders, 'cycles_found': cycles,
           'min_cut': result['min_cut']['accounts'], 'min_cut_verified': result['min_cut'].get('verified'), 'min_cut_note': result['min_cut'].get('error'),
           'greedy_freeze': result['freeze_ids'], 'senders_after_greedy': result['after']['senders_reaching_collector'],
           'senders_before': result['before']['senders_reaching_collector'], 'scope_accounts': len(result['params']['scope_ids'])}}
    (ROOT / 'eval/scale.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
