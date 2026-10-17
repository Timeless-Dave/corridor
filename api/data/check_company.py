"""Read-only verification of the seeded company graph; never calls a model."""
import json
from agent.tools import CorridorTools
from db import connect, DatabaseError


def inspect_company(graph):
    tools = CorridorTools(graph)
    result = {}
    expected = {'US-NG': ('emp_0', 'team_0', range(1, 5)),
                'NG-US': ('emp_1', 'team_1', range(5, 7))}
    decisions = {1: {'DEC-6'}, 2: {'DEC-1', 'DEC-7'}, 3: {'DEC-2'},
                 4: {'DEC-3'}, 5: {'DEC-4'}, 6: {'DEC-5'}}
    for corridor, (lead, team, numbers) in expected.items():
        rows = tools.corridor_context(corridor)
        if len(rows) != 1:
            raise ValueError('Expected one company context per seeded corridor.')
        context = rows[0]
        if (context['lead_id'], context['team_id']) != (lead, team):
            raise ValueError('Unexpected seeded corridor owner or lead.')
        policies = {p['id']: p for p in context['policies']}
        if set(policies) != {f'POL-AML-{i}' for i in numbers}:
            raise ValueError('Unexpected seeded corridor policies.')
        precedents = {}
        for i in numbers:
            policy = f'POL-AML-{i}'
            if policies[policy]['source_id'] != f'DOC-{i}':
                raise ValueError('Policy source document mismatch.')
            precedents[policy] = tools.precedents(policy)
            if {r['decision'] for r in precedents[policy]} != decisions[i]:
                raise ValueError('Current precedent mismatch; inspect supersession links.')
        result[corridor] = {'context': context, 'precedents': precedents}
    result['experts'] = tools.who_knows('fan_in_mule')
    if not any(r['employee_id'] == 'emp_6' for r in result['experts']):
        raise ValueError('Seeded historical decision author not found.')
    return result


def main():
    try:
        print(json.dumps({'verified': True, 'company': inspect_company(connect())}, indent=2))
        return 0
    except (DatabaseError, ValueError) as error:
        print(json.dumps({'verified': False, 'error': str(error)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
