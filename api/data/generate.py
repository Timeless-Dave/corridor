"""Deterministic, entirely fictional fixtures; no wall-clock inputs."""
import argparse
import json
import random
from pathlib import Path

BASE_TS = 1792065600
DATA_DIR = Path(__file__).resolve().parent


def generate(seed=42):
    rng = random.Random(seed)
    nodes, edges = [], []
    countries = {}
    def node(label, key, **props):
        nodes.append({'label': label, 'key': key, 'props': props})
        return key
    def edge(kind, source, target, **props):
        edges.append({'type': kind, 'source': source, 'target': target, 'props': props})
    def person(key):
        node('Person', key, id=key, name=f'Fictional person {key}', country='US')
    def account(key, owner, country='US', kyc=2):
        countries[key] = country
        node('Account', key, id=key, country=country, type='personal',
             opened_at=BASE_TS-86400*365, kyc_tier=kyc, flagged=False)
        edge('OWNS', owner, key)
    def device(key):
        node('Device', key, fingerprint=key, os='synthetic-os')
    def used(a, d):
        edge('USED', a, d, first_seen=BASE_TS-86400, last_seen=BASE_TS)
    def sent(a, b, amount, ts, **extra):
        key = f'tx_{len(edges):07d}'
        edge('SENT', a, b, id=key, amount=amount, currency='USD', ts=ts,
             corridor=f'{countries[a]}-{countries[b]}', **extra)
        return key
    for i in range(2000):
        p, a = f'person_{i:04d}', f'acct_{i:04d}'
        person(p)
        account(a, p, 'US' if i < 1000 else 'NG')
        # One device per pair for 20 benign family pairs; otherwise unique.
        d = f'device_{i//2 if i < 40 else i:04d}'
        if not any(n['key'] == d for n in nodes):
            device(d)
        used(a, d)
        ph = f'phone_{i:04d}'
        node('Phone', ph, number=ph, country=countries[a])
        edge('REGISTERED', a, ph)
    for _ in range(20000):
        i = rng.randrange(1000)
        j = rng.randrange(1000, 2000)
        if rng.random() < .2:
            i, j = j, i
        sent(f'acct_{i:04d}', f'acct_{j:04d}', round(min(2500, rng.lognormvariate(5, .7)), 2),
             BASE_TS-rng.randrange(86400*30))
    for i in range(10):
        m = f'merchant_{i}'
        node('Merchant', m, id=m, name=f'Fictional merchant {i}', category='groceries')
        edge('PAID', f'acct_{1000+i:04d}', m, amount=25.0, ts=BASE_TS)
    cycle = [f'cycle_{i}' for i in range(5)]
    cluster = cycle[:2] + [f'shared_{i}' for i in range(7)]
    for i in range(4):
        person(f'shared_owner_{i}')
    for i, a in enumerate(cluster):
        account(a, f'shared_owner_{i%4}', 'US' if i%2 == 0 else 'NG')
    for a in cycle[2:]:
        person(f'owner_{a}')
        account(a, f'owner_{a}', 'NG')
    for i in range(2):
        device(f'shared_device_{i}')
    for i in range(3):
        node('Phone', f'shared_phone_{i}', number=f'shared_phone_{i}', country='US')
    for i, a in enumerate(cluster):
        used(a, f'shared_device_{i%2}')
        if i == 0:
            used(a, 'shared_device_1')
        edge('REGISTERED', a, f'shared_phone_{i%3}')
    cycle_txs = [sent(a, cycle[(i+1)%5], 480.0-i*5, BASE_TS+i*3600)
                 for i, a in enumerate(cycle)]
    senders = [f'mule_{i}' for i in range(12)]
    collector = 'collector_0'
    for a in senders+[collector]:
        person(f'owner_{a}')
        account(a, f'owner_{a}', 'NG' if a == collector else 'US', 1)
    for i, a in enumerate(senders):
        sent(a, collector, 400.0+i, BASE_TS+i*3600)
    def pool(key, members, abusive=False):
        node('AjoPool', key, id=key, name=f'Fictional pool {key}', contribution=50.0, cycle_days=7)
        for i, a in enumerate(members):
            edge('MEMBER_OF', a, key, round_position=i)
        for r in range(3):
            recipient = members[0] if abusive else members[r]
            for a in members:
                if a != recipient:
                    sent(a, recipient, 50.0, BASE_TS+r*7*86400, pool_id=key, round=r,
                         purpose='ajo_payout')
    for i in range(30):
        pool(f'pool_{i:02d}', [f'acct_{1000+i*5+j:04d}' for j in range(5)])
    abusive = [f'ajo_{i}' for i in range(5)]
    device('ajo_device')
    for a in abusive:
        person(f'owner_{a}')
        account(a, f'owner_{a}', 'NG')
        used(a, 'ajo_device')
    pool('pool_abuse', abusive, True)
    for i in range(3):
        node('Team', f'team_{i}', id=f'team_{i}', name=f'Fictional team {i}')
    for i in range(12):
        e = f'emp_{i}'
        node('Employee', e, id=e, name=f'Fictional employee {i}', role='corridor lead' if i<2 else 'analyst')
        edge('MEMBER_OF', e, f'team_{i%3}')
    for i, code in enumerate(('US-NG', 'NG-US')):
        node('Corridor', code, code=code)
        edge('OWNS', f'team_{i}', code)
        edge('LEADS', f'emp_{i}', code)
    for i in range(6):
        p, d = f'POL-AML-{i+1}', f'DOC-{i+1}'
        node('Policy', p, id=p, title=f'Synthetic review policy {i+1}',
             rule='Fictional demo: investigate connected evidence; this is not a legal threshold.', threshold=500.0)
        node('Doc', d, id=d, title=f'Fictional handbook {i+1}', source='synthetic', updated_at=BASE_TS)
        edge('DEFINES', d, p)
        edge('APPLIES_TO', p, 'US-NG' if i<4 else 'NG-US')
    for i in range(8):
        d = f'DEC-{i}'
        node('Decision', d, id=d, summary=f'Fictional precedent {i}', date=BASE_TS-(8-i)*86400,
             outcome='FREEZE' if i in (0, 6) else 'MONITOR')
        edge('MADE_BY', d, f'emp_{i}')
        edge('BASED_ON', d, f'POL-AML-{i%6+1}')
    edge('SUPERSEDES', 'DEC-6', 'DEC-0')
    node('Case', 'case_history', id='case_history', status='closed', verdict='FREEZE', risk=.9,
         opened_at=BASE_TS-86400*7, closed_at=BASE_TS-86400*6, pattern='fan_in_mule')
    edge('INVOLVES', 'case_history', senders[0], role='flagged')
    edge('PRECEDENT', 'case_history', 'DEC-6')
    edge('APPLIED', 'case_history', 'POL-AML-1')
    edge('ASSIGNED_TO', 'case_history', 'emp_0')
    node('Finding', 'finding_history', id='finding_history', step=1, text='Synthetic historical review.',
         tool='seed_history', query_name='seed_history', params='{}', created_at=BASE_TS-86400*7)
    edge('HAS_FINDING', 'case_history', 'finding_history')
    edge('CITES', 'finding_history', senders[0])
    for n in nodes:
        if n['label'] == 'Account' and n['key'] in (cycle[0], collector, cluster[2], abusive[0]):
            n['props']['flagged'] = True
    truth = {'seed': seed, 'reference_ts': BASE_TS, 'rings': {
        'cycle': {'accounts': cycle, 'transfers': cycle_txs, 'params': {'account_id': cycle[0]}},
        'fan_in': {'accounts': senders+[collector], 'params': {'account_id': collector, 'since': BASE_TS-1,
                                                           'until': BASE_TS+48*3600, 'max_amount': 500.0}},
        'shared': {'accounts': cluster, 'params': {'account_id': cycle[0]}},
        'ajo': {'accounts': abusive, 'params': {'pool_id': 'pool_abuse'}}},
        'controls': {'family_account': 'acct_0000', 'legitimate_pool': 'pool_00'}}
    return {'nodes': nodes, 'edges': edges}, truth


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output-dir', type=Path, default=DATA_DIR)
    args = parser.parse_args()
    dataset, truth = generate(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in [('dataset', dataset), ('ground_truth', truth)]:
        (args.output_dir / f'{name}.json').write_text(json.dumps(value, sort_keys=True, indent=2)+'\n')
    print(f'Generated {len(dataset["nodes"])} nodes and {len(dataset["edges"])} edges (seed {args.seed}).')

if __name__ == '__main__':
    main()
