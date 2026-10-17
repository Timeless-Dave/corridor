"""Load the generated dataset through static, parameterized query files."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from agent.tools import run_query
from db import connect, DatabaseError
from data.generate import DATA_DIR

INDEX_LABELS = ('Account', 'Device', 'Phone', 'Case', 'Corridor', 'Policy')


def validate(data):
    nodes = {n['key']: n for n in data['nodes']}
    if len(nodes) != len(data['nodes']):
        raise ValueError('Duplicate node identifiers.')
    for n in nodes.values():
        prop = {'Device': 'fingerprint', 'Phone': 'number', 'Corridor': 'code'}.get(n['label'], 'id')
        if n['props'].get(prop) != n['key']:
            raise ValueError('Node identity does not match its natural key.')
    tx_ids = set()
    for e in data['edges']:
        if e['source'] not in nodes or e['target'] not in nodes:
            raise ValueError('Relationship references an unknown node.')
        if e['type'] == 'SENT':
            if e['props']['id'] in tx_ids:
                raise ValueError('Duplicate transfer identifiers.')
            tx_ids.add(e['props']['id'])
    return nodes


def load(graph, data, reset=False, batch_size=500):
    nodes = validate(data)
    groups = defaultdict(list)
    for n in data['nodes']:
        groups[f'load_node_{n["label"]}'].append(n)
    edge_groups = defaultdict(list)
    for e in data['edges']:
        source, target = nodes[e['source']]['label'], nodes[e['target']]['label']
        edge_groups[f'load_edge_{e["type"]}_{source}_{target}'].append(e)
    # Validate the query registry before touching the target graph.
    from agent.tools import QUERIES
    if not (groups.keys() | edge_groups.keys()) <= QUERIES.keys():
        raise ValueError('Dataset contains an unsupported node or relationship type.')
    if batch_size < 1:
        raise ValueError('Batch size must be positive.')
    try:
        names = graph.client.list_graphs()
        exists = graph.name in [n.decode() if isinstance(n, bytes) else n for n in names]
    except Exception:
        raise DatabaseError('Cannot list graphs; check remote connectivity and credentials.') from None
    existing = run_query(graph, 'count_nodes', readonly=True)[0][0] if exists else 0
    if existing and not reset:
        raise ValueError('Graph is populated. Use --reset only to replace this configured graph.')
    if reset and exists:
        try:
            graph.delete()
        except Exception:
            raise DatabaseError('Cannot reset configured graph.') from None
    for label in INDEX_LABELS:
        run_query(graph, f'index_{label}')
    for grouping in (groups, edge_groups):
        for name, rows in grouping.items():
            for start in range(0, len(rows), batch_size):
                batch = rows[start:start+batch_size]
                result = run_query(graph, name, {'rows': batch})
                if result != [[len(batch)]]:
                    raise ValueError(f'Incomplete load in {name}; explicit reset required before retry.')
    return {'nodes': run_query(graph, 'node_counts', readonly=True),
            'edges': run_query(graph, 'edge_counts', readonly=True)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true')
    parser.add_argument('--dataset', type=Path, default=DATA_DIR/'dataset.json')
    args = parser.parse_args()
    try:
        data = json.loads(args.dataset.read_text())
        print(json.dumps(load(connect(), data, reset=args.reset), indent=2))
    except DatabaseError as error:
        print(str(error))
        raise SystemExit(1)
    except (ValueError, OSError):
        print('Load failed. Check dataset and graph occupancy; a populated graph requires explicit --reset.')
        raise SystemExit(1)

if __name__ == '__main__':
    main()
