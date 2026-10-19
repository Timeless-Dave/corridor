"""Held-out evaluation worlds: unseen seed, jittered planted transfers, anonymized identifiers.

The development data names accounts after their role (collector_0, mule_3, family_0_0).
Here every account, device, phone, pool and person gets a random id, so the model cannot
read the answer from a name. Planted transfers keep their shape (who pays whom, in which
order, under the threshold) but get a per-world time shift and amount jitter.
"""
import random
from data.generate import generate

PREFIX = {'Account': 'acct', 'Device': 'dev', 'Phone': 'ph', 'AjoPool': 'pool', 'Person': 'person'}
KEY_PROP = {'Device': 'fingerprint', 'Phone': 'number'}
THRESHOLD = 500.0


def world(seed):
    data, truth = generate(seed)
    rng = random.Random(seed * 7919)
    planted = set()
    for ring in truth['rings'].values():
        planted.update(ring['accounts'])
    for decoy in truth.get('decoys', []):
        planted.update(decoy['members'])
    shift = rng.randint(1, 20) * 86400 + rng.randint(0, 23) * 3600
    # One factor per world keeps each ring's shape: skimming cycles stay strictly decreasing,
    # small transfers stay under the threshold and large ones stay above it.
    small, large = rng.uniform(0.85, 1.0), rng.uniform(1.0, 1.15)
    for e in data['edges']:
        if e['type'] == 'SENT' and (e['source'] in planted or e['target'] in planted):
            p = e['props']
            p['ts'] += shift
            p['amount'] = round(p['amount'] * (small if p['amount'] < THRESHOLD else large), 2)
    mapping, used = {}, set()
    for n in data['nodes']:
        prefix = PREFIX.get(n['label'])
        if not prefix: continue
        while True:
            new = f'{prefix}_{rng.getrandbits(32):08x}'
            if new not in used: break
        used.add(new); mapping[n['key']] = new
        n['key'] = new
        n['props'][KEY_PROP.get(n['label'], 'id')] = new
        if 'name' in n['props']: n['props']['name'] = f"Fictional {n['label'].lower()} {new}"
    for e in data['edges']:
        e['source'] = mapping.get(e['source'], e['source'])
        e['target'] = mapping.get(e['target'], e['target'])
        if e['type'] == 'SENT':
            e['props']['id'] = f'tx_{rng.getrandbits(48):012x}'  # sequential ids would reveal planted transfers
        if e['type'] == 'SENT' and e['props'].get('pool_id'):
            e['props']['pool_id'] = mapping.get(e['props']['pool_id'], e['props']['pool_id'])
    flags = [{'account_id': mapping[f['account_id']], 'expected_ring_member': f['expected_ring_member'],
              'original_role': f['account_id']} for f in truth['evaluation_flags']]
    return data, flags
