"""Bounded counterfactuals on disposable graph copies. No real payment integration."""
from contextlib import contextmanager
import hashlib
import json
import threading
import time
import uuid
from agent.tools import query_records, _ids
from db import DatabaseError

# Single-worker demo: serializes simulation, approval and in-process snapshot checks.
INTERVENTION_LOCK = threading.RLock()


def digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@contextmanager
def copy_graph(graph, case_id):
    # Never interpolate a user identifier into a database command key.
    name = graph.name + '_sim_' + uuid.uuid4().hex
    clone = None
    try:
        for attempt in range(5):
            try:
                clone = graph.copy(name)
                break
            except Exception as error:
                # GRAPH.COPY forks the server, which refuses concurrent forks; wait and retry.
                if 'fork' not in str(error) or attempt == 4: raise
                time.sleep(1 + attempt)
        yield clone
    except DatabaseError:
        raise
    except Exception:
        raise DatabaseError('Scratch graph operation failed; intervention was not approved.') from None
    finally:
        if clone is not None:
            try:
                clone.delete()
            except Exception:
                raise DatabaseError('Scratch graph cleanup failed; inspect disposable graph keys.') from None


def measure(graph, params):
    reaching = query_records(graph, 'sim_reach', params)
    inflow = query_records(graph, 'sim_inflow', params)[0]
    cycles = query_records(graph, 'sim_cycles', params)[0]
    return {**inflow, **cycles, 'senders_reaching_collector': len(reaching),
            'reachable_sender_ids': [r['sender'] for r in reaching]}


def scope(graph, case_id, account_ids):
    rows = query_records(graph, 'sim_scope', {'case_id': case_id})
    if not rows: raise ValueError('Case not found.')
    collector = rows[0]['collector']
    observed = set(rows[0]['accounts']) | {collector}
    ring = _ids(account_ids)
    if not ring or not set(ring) <= observed:
        raise ValueError('Simulation candidates must be accounts cited in this case.')
    ring = sorted(set(ring) | {collector})
    metadata = query_records(graph, 'account_context', {'account_id': collector})
    latest = metadata[0]['latest_transfer_ts'] if metadata else None
    if latest is None: raise ValueError('No transfers available for intervention measurement.')
    params = {'account_ids': ring, 'since': max(0, latest - 259200), 'until': latest}
    edges = query_records(graph, 'sim_edges', params)
    ids = sorted(set(ring) | {e[k] for e in edges for k in ('source', 'target')})
    if len(ids) > 200: raise ValueError('Scope exceeds 200 accounts; narrow the investigation before simulation.')
    params.update(collector=collector, scope_ids=ids, sender_ids=[a for a in ids if a != collector])
    # Fingerprint the complete bounded neighborhood, including blocked flags.
    snapshot = query_records(graph, 'sim_edges', {**params, 'account_ids': ids})
    return ring, params, snapshot


def min_cut(scratch, params, candidates, senders):
    """Exact minimum vertex cut between reachable senders and the collector (max-flow on a node-split network)."""
    if not senders: return {'size': 0, 'accounts': [], 'max_flow': 0.0}
    query_records(scratch, 'sim_flow_nodes', {'scope_ids': params['scope_ids'], 'candidate_ids': candidates}, readonly=False)
    query_records(scratch, 'sim_flow_edges', params, readonly=False)
    try:
        row = query_records(scratch, 'sim_max_flow', {'sender_ids': senders, 'collector': params['collector']})[0]
    except DatabaseError:
        # algo.maxFlow ships in newer FalkorDB releases (Cloud 4.22 has it; embedded 4.18 does not).
        return {'size': None, 'accounts': [], 'max_flow': None, 'error': 'algo.maxFlow unavailable on this FalkorDB server'}
    flows = {tuple(e): f for e, f in zip(row['edges'], row['edgeFlows'])}
    net = query_records(scratch, 'sim_flow_network')
    forward, backward = {}, {}
    for e in net:
        u, v = (e['source'], e['source_side']), (e['target'], e['target_side'])
        f = flows.get((*u, *v), 0.0)
        if f < e['cap'] - 1e-9: forward.setdefault(u, []).append(v)
        if f > 1e-9: backward.setdefault(v, []).append(u)
    # Residual reachability from every source; split edges leaving it form the cut.
    seen = {(s, 'in') for s in senders}
    stack = list(seen)
    while stack:
        u = stack.pop()
        for v in forward.get(u, []) + backward.get(u, []):
            if v not in seen: seen.add(v); stack.append(v)
    cut = sorted(e['source'] for e in net if e['source_side'] == 'in' and e['target_side'] == 'out'
                 and (e['source'], 'in') in seen and (e['source'], 'out') not in seen)
    feasible = row['maxFlow'] < 100000.0
    return {'size': len(cut) if feasible else None, 'accounts': cut if feasible else [], 'max_flow': row['maxFlow']}


def plan(graph, case_id, account_ids, *, freeze_ids=None, k=4):
    if type(k) is not int or not 1 <= k <= 4: raise ValueError('Freeze budget must be between 1 and 4.')
    with INTERVENTION_LOCK:
        ring, params, snapshot = scope(graph, case_id, account_ids)
        specified = _ids(freeze_ids) if freeze_ids is not None else None
        if specified is not None and (not specified or not set(specified) <= set(ring) or len(specified) > 4):
            raise ValueError('Choose one to four observed candidate accounts.')
        with copy_graph(graph, case_id) as scratch:
            # All measurements/ranking use the same consistent copied graph.
            ring, params, snapshot = scope(scratch, case_id, ring)
            ranks = query_records(scratch, 'collector_rank', {'account_ids': ring})
            communities = query_records(scratch, 'sim_communities')
            by_id = {r['account']: r['community_id'] for r in communities}
            community = {a for a, c in by_id.items() if c == by_id.get(params['collector'])}
            before = measure(scratch, params)
            exact = min_cut(scratch, params, ring, before['reachable_sender_ids'])
            order = specified if specified is not None else [r['account'] for r in ranks][:k]
            selected, steps = [], []
            for account in order:
                if specified is None and steps and steps[-1]['after']['senders_reaching_collector'] == 0: break
                if specified is None and not before['senders_reaching_collector']: break
                selected.append(account)
                query_records(scratch, 'sim_remove', {'freeze_ids': [account]}, readonly=False)
                after = measure(scratch, params)
                counterparties = {e['target'] if e['source'] in selected else e['source'] for e in snapshot
                                  if not e['blocked'] and (e['source'] in selected or e['target'] in selected)} - set(selected)
                steps.append({'account': account, 'after': after,
                              'outside_community_counterparties': sorted(counterparties - community),
                              'outside_candidate_counterparties': sorted(counterparties - set(ring))})
            result = {'plan_id': 'plan_' + uuid.uuid4().hex, 'case_id': case_id, 'collector': params['collector'],
                      'accounts': ring, 'freeze_ids': selected, 'before': before,
                      'after': steps[-1]['after'] if steps else before, 'steps': steps, 'ranking': ranks,
                      'community_members': sorted(community), 'params': params, 'fingerprint': digest(snapshot),
                      'method': 'Specified candidates' if specified is not None else 'PageRank-ordered greedy heuristic; not a minimum-set guarantee',
                      'scope': 'Up to 5 directed hops inside the cited accounts and their one-hop transfer neighbors, over 72 hours. Historical flows model blocked routes, not future savings.',
                      'synthetic': True, 'scratch_deleted': True}
        if exact['accounts']:
            # Prove the exact cut on its own fresh copy rather than trusting the max-flow value.
            with copy_graph(graph, case_id) as check:
                query_records(check, 'sim_remove', {'freeze_ids': exact['accounts']}, readonly=False)
                exact['after'] = measure(check, params)
            exact['verified'] = exact['after']['senders_reaching_collector'] == 0
        result['min_cut'] = exact
        # Saving happens only after successful cleanup; failures cannot claim deletion.
        query_records(graph, 'sim_save_plan', {'case_id': case_id, 'plan_id': result['plan_id'],
            'payload': json.dumps(result, sort_keys=True), 'fingerprint': result['fingerprint'], 'now': int(time.time())}, readonly=False)
        return [result]


def get_plan(graph, case_id, plan_id=''):
    rows = query_records(graph, 'sim_get_plan', {'case_id': case_id, 'plan_id': plan_id})
    return json.loads(rows[0]['payload']) if rows else None


def approve(graph, case_id, plan_id):
    with INTERVENTION_LOCK:
        p = get_plan(graph, case_id, plan_id)
        if not p or not p['freeze_ids']: raise ValueError('A measured nonempty plan is required.')
        audit = query_records(graph, 'investigation_audit', {'case_id': case_id})[0]
        if audit['case'].get('verdict') != 'FREEZE' or audit['case'].get('status') != 'closed':
            raise ValueError('Only a closed FREEZE case can authorize a modeled intervention.')
        # A case-wide FREEZE is insufficient permission to block an unrelated member.
        from agent.guardrails import positive_evidence
        evidence = query_records(graph, 'case_evidence', {'case_id': case_id})
        citations = {f['finding_id']: set(f['cited']) for f in evidence}
        supports = {account: set() for account in p['freeze_ids']}
        for finding in audit['findings']:
            try:
                rows = json.loads(finding.get('result_json') or '[]')
                positive = positive_evidence(finding.get('tool'), rows)
            except (TypeError, ValueError, KeyError):
                positive = False
            if positive:
                for account in supports:
                    if account in citations.get(finding['id'], set()): supports[account].add(finding['tool'])
        if any(len(v) < 2 for v in supports.values()):
            raise ValueError('Every frozen account needs two independent positive evidence tools. Narrow the plan or investigate further.')
        params = p['params']
        snapshot = query_records(graph, 'sim_edges', {**params, 'account_ids': params['scope_ids']})
        if digest(snapshot) != p['fingerprint']: raise ValueError('Graph changed since simulation. Run a new simulation before approval.')
        existing = query_records(graph, 'sim_orders', {'case_id': case_id})
        if existing: raise ValueError('This case already has an intervention; inspect its receipt.')
        before = measure(graph, params)
        if before != p['before']: raise ValueError('Measurement changed. Run a new simulation.')
        oid = 'freeze_' + uuid.uuid4().hex
        rows = query_records(graph, 'sim_approve', {'case_id': case_id, 'plan_id': plan_id,
            'order_id': oid, 'now': int(time.time()), 'freeze_ids': p['freeze_ids']}, readonly=False)
        if not rows: raise ValueError('Approval rejected; inspect case and plan state.')
        # If this read/write fails, the durable pending_measurement order is visible.
        after = measure(graph, params)
        query_records(graph, 'sim_receipt', {'order_id': oid, 'measurement_id': 'measurement_' + uuid.uuid4().hex,
            'before': json.dumps(before), 'after': json.dumps(after), 'now': int(time.time()),
            'matched': after == p['after']}, readonly=False)
        return {'order_id': oid, 'before': before, 'after': after, 'matched_projection': after == p['after'],
                'synthetic': True, 'freeze_ids': p['freeze_ids']}
