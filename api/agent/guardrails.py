"""Deterministic evidence and verdict checks; never delegated to the model."""
from collections import defaultdict


def candidate_ids(tool,params,rows):
    ids=set()
    fields={'account','accounts','collector','sender_ids','member','members','contributors',
            'shared_devices','identifier','path','decision','known_bad',
            'employee_id','lead_id','team_id','decided_by_id'}
    for row in rows:
        for key in fields:
            value=row.get(key,[])
            if isinstance(value,str): ids.add(value)
            elif isinstance(value,list): ids.update(v for v in value if isinstance(v,str))
        for p in row.get('policies',[]):
            if p.get('id'): ids.add(p['id'])
            if p.get('source_id'): ids.add(p['source_id'])
    # A nonempty result establishes the query's starting account; zero rows do not.
    if rows and params.get('account_id'):
        ids.add(params['account_id'])
    return sorted(ids)


def positive_evidence(tool,rows):
    if tool=='circular_flows': return bool(rows)
    if tool=='shared_identifiers': return len({r['account'] for r in rows})>=3
    if tool=='fan_in': return any(r['senders']>=12 for r in rows)
    if tool=='ajo_payout_pattern': return any(r['shared_devices'] and r['next_round']==r['first_round']+1 for r in rows)
    if tool=='link_to_known_bad': return any(r['hops']>0 for r in rows)
    # Structural algorithms, metadata, empty results, and memory are not independent
    # suspicious findings. Conservative by design for a synthetic demonstration.
    return False


def apply(proposed,findings,account_id,context,precedents,prior_freeze=False,force_monitor=False):
    decision=dict(proposed)
    reasons=[]
    account_ids={account_id}
    supports=defaultdict(set)
    for finding in findings:
        account_ids.update(finding.get('account_ids',[]))
        if finding.get('positive') and not finding.get('error'):
            for account in set(finding['cited_ids']) & set(finding.get('account_ids',[])):
                supports[account].add(finding['tool'])
    valid_members=list(dict.fromkeys(m for m in proposed['members'] if m in account_ids))
    if set(valid_members)!=set(proposed['members']): reasons.append('Removed members absent from graph evidence.')
    if account_id not in valid_members: valid_members.insert(0,account_id)
    decision['members']=valid_members
    if decision['verdict']=='FREEZE' and not any(len(supports[a])>=2 for a in valid_members):
        decision['verdict']='MONITOR'
        reasons.append('FREEZE downgraded: no member has two positive independent tools citing the same account.')
    completed={f['tool'] for f in findings if f.get('result') and not f.get('error')}
    if decision['verdict']=='FREEZE' and not completed.intersection({'collector_rank','ring_communities'}):
        decision['verdict']='MONITOR'
        reasons.append('FREEZE downgraded: structural algorithm evidence was not recorded.')
    plans=[r for f in findings if f['tool']=='min_freeze_set' and not f.get('error') for r in f.get('result',[])]
    if decision['verdict']=='FREEZE' and not any(p.get('scratch_deleted') and p.get('freeze_ids') for p in plans):
        decision['verdict']='MONITOR'
        reasons.append('FREEZE downgraded: no completed nonempty scratch-graph intervention plan.')
    policy_ids={p['id'] for r in context for p in r['policies'] if p.get('id')}
    lead_ids={r['lead_id'] for r in context if r.get('lead_id')}
    decision_ids={r['decision'] for r in precedents}
    grounded=(decision['policy_id'] in policy_ids and decision['precedent_decision_id'] in decision_ids
              and decision['assignee_employee_id'] in lead_ids)
    if force_monitor:
        decision['verdict']='MONITOR'
        reasons.append('Model or tool error requires review; automatic CLEAR/FREEZE suppressed.')
    if prior_freeze:
        decision['risk']=max(decision['risk'],0.7)
        reasons.append('Prior FREEZE found; deterministic risk floor is 0.7.')
    decision['risk']=float(decision['risk'])
    return decision,reasons,grounded
