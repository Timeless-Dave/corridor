"""Non-graph rule baselines on the same 12 evaluation flags the agent is scored on.

Each rule looks at one account's own transfers or identifiers, the way a per-transaction
monitoring rule would. Rules are fixed in advance and not tuned to the flags.
Run: PYTHONPATH=api .venv/bin/python eval/baselines.py
"""
import json
from collections import defaultdict
from pathlib import Path
from data.generate import generate

ROOT = Path(__file__).resolve().parents[1]
THRESHOLD = 500.0      # the demo policies' review threshold (POL-AML-*)
VELOCITY = 10          # incoming transfers within 48 hours
DEVICE_PEERS = 3       # other accounts on a shared device or phone
WINDOW = 172800


def main():
    data, _ = generate(42)
    edges = data['edges']
    sent = [e for e in edges if e['type'] == 'SENT']
    by_account = defaultdict(list)
    incoming = defaultdict(list)
    for e in sent:
        by_account[e['source']].append(e['props'])
        by_account[e['target']].append(e['props'])
        incoming[e['target']].append(e['props']['ts'])
    users = defaultdict(set)
    for e in edges:
        if e['type'] in ('USED', 'REGISTERED'):
            users[e['target']].add(e['source'])

    def amount_rule(a):
        return any(t['amount'] >= THRESHOLD for t in by_account[a])

    def velocity_rule(a):
        ts = sorted(incoming[a])
        return any(sum(1 for u in ts[i:] if u - t <= WINDOW) >= VELOCITY for i, t in enumerate(ts))

    def device_rule(a):
        peers = set().union(set(), *[us for us in users.values() if a in us])
        return len(peers - {a}) >= DEVICE_PEERS

    gt = json.loads((ROOT / 'api/data/ground_truth.json').read_text())
    expected = {f['account_id']: f['expected_ring_member'] for f in gt['evaluation_flags']}
    rules = {'Per-transfer amount ≥ $500': amount_rule, 'Incoming velocity ≥ 10 in 48h': velocity_rule,
             'Shared device/phone with ≥ 3 accounts': device_rule}
    agent = json.loads((ROOT / 'eval/results.json').read_text())
    agent_alert = {r['account_id']: r['verdict'] in ('FREEZE', 'MONITOR') for r in agent['results']}
    rows = []
    for name, rule in list(rules.items()) + [('Any of the three rules', lambda a: any(r(a) for r in rules.values())),
                                             ('Corridor agent (eval/results.json)', lambda a: agent_alert[a])]:
        alerts = {a: bool(rule(a)) for a in expected}
        tp = sum(alerts[a] and expected[a] for a in expected); fp = sum(alerts[a] and not expected[a] for a in expected)
        fn = sum((not alerts[a]) and expected[a] for a in expected); tn = sum((not alerts[a]) and not expected[a] for a in expected)
        rows.append({'method': name, 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
                     'precision': round(tp / (tp + fp), 2) if tp + fp else None, 'recall': round(tp / (tp + fn), 2),
                     'alerted': sorted(a for a in alerts if alerts[a])})
    out = {'flags': len(expected), 'rings': sum(expected.values()), 'decoys': sum(not v for v in expected.values()),
           'parameters': {'amount_threshold': THRESHOLD, 'velocity': VELOCITY, 'window_s': WINDOW, 'device_peers': DEVICE_PEERS},
           'results': rows}
    (ROOT / 'eval/baselines.json').write_text(json.dumps(out, indent=2) + '\n')
    for r in rows:
        print(f"{r['method']:40} rings {r['tp']}/{r['tp'] + r['fn']}  decoys {r['fp']}/{r['fp'] + r['tn']}  P={r['precision']} R={r['recall']}")


if __name__ == '__main__':
    main()
