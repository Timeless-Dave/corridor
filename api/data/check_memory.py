"""Run two real investigations and verify cross-account memory from stored findings."""
import argparse
import json
from pathlib import Path

from agent.loop import Investigation, InvestigationError
from agent.model import OpenAIModel, ModelError
from agent.tools import query_records
from db import connect, DatabaseError


def verify_memory(graph, model, account='collector_0', on_event=None):
    first = Investigation(graph, model, on_event=on_event).run(account)
    state = query_records(graph, 'case_state', {'case_id': first['case_id']})[0]
    if state['status'] != 'closed':
        raise ValueError('First case did not close.')
    members = sorted({m['id'] for m in state['members'] if m['id'] and m['id'] != account})
    if not members:
        raise ValueError('First case has no other persisted member; memory demo cannot proceed.')
    second_account = members[0]
    # A fresh loop retrieves the earlier case from FalkorDB, not Python conversation state.
    second = Investigation(graph, model, on_event=on_event).run(second_account)
    evidence = query_records(graph, 'case_evidence', {'case_id': second['case_id']})
    first_step = min(evidence, key=lambda row: row['step'])
    if first_step['tool'] != 'prior_cases' or first_step['step'] != 1:
        raise ValueError('Second case did not check memory on step one.')
    audit = query_records(graph, 'investigation_audit', {'case_id': second['case_id']})[0]
    finding = next(f for f in audit['findings'] if f['step'] == 1)
    rows = json.loads(finding['result_json'])
    matched = [row for row in rows if row['case_id'] == first['case_id']]
    if not matched or any(row['case_id'] == second['case_id'] for row in rows):
        raise ValueError('Persisted step-one memory did not retrieve the earlier case correctly.')
    if audit['case']['status'] != 'closed':
        raise ValueError('Second case did not close.')
    return {'verified': True, 'first_account': account, 'second_account': second_account,
            'first_case': first, 'second_case': second, 'step_one': finding,
            'matched_prior_case': matched, 'browser_paths': [f"/cases/{first['case_id']}", f"/cases/{second['case_id']}"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--account', default='collector_0')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        model = OpenAIModel()
        report = verify_memory(connect(), model, args.account,
                               on_event=lambda e: print(json.dumps({'type': e['type'], 'case_id': e['case_id'], 'tool': e.get('tool')}), flush=True))
        if args.output:
            args.output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
        return 0
    except (DatabaseError, ModelError, InvestigationError, ValueError) as error:
        print(json.dumps({'verified': False, 'error': str(error)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
