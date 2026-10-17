"""Read-only proof runner; displays parameters and observed graph evidence."""
import json
from agent.tools import run_query
from data.generate import DATA_DIR
from db import connect, DatabaseError


def verify(graph, truth):
    results = {}
    for pattern, fixture in truth['rings'].items():
        rows = run_query(graph, f'proof_{pattern}', fixture['params'], readonly=True)
        if not rows:
            raise ValueError(f'No evidence for {pattern}')
        results[pattern] = {'params': fixture['params'], 'evidence': rows}
    cycle = results['cycle']['evidence'][0]
    assert cycle[0] == truth['rings']['cycle']['accounts'] + [truth['rings']['cycle']['accounts'][0]]
    assert cycle[1] == truth['rings']['cycle']['transfers']
    assert cycle[2] == [480.0, 475.0, 470.0, 465.0, 460.0]
    assert cycle[3] == [truth['reference_ts'] + i * 3600 for i in range(5)]
    fan = results['fan_in']['evidence'][0]
    assert fan[1] == 12 and set(fan[2]) == set(truth['rings']['fan_in']['accounts'][:-1])
    shared = results['shared']['evidence'][0]
    assert set(shared[0]) == set(truth['rings']['shared']['accounts'])
    assert [len(x) for x in shared] == [9, 4, 2, 3]
    ajo = results['ajo']['evidence']
    assert [(r[1], r[2]) for r in ajo] == [(0, 1), (1, 2)]
    assert all(r[0] == 'ajo_0' and set(r[3]) == set(truth['rings']['ajo']['accounts'][1:]) for r in ajo)
    assert run_query(graph, 'proof_ajo', {'pool_id': truth['controls']['legitimate_pool']}, readonly=True) == []
    family = run_query(graph, 'proof_shared', {'account_id': truth['controls']['family_account']}, readonly=True)
    assert len(family[0][0]) == 2
    return results


def main():
    try:
        truth = json.loads((DATA_DIR/'ground_truth.json').read_text())
        print(json.dumps(verify(connect(), truth), indent=2))
    except DatabaseError as error:
        print(str(error))
        raise SystemExit(1)
    except (AssertionError, ValueError):
        print('Graph evidence does not match the expected fixtures.')
        raise SystemExit(1)

if __name__ == '__main__':
    main()
