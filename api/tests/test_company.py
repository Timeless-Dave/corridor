"""M4 routing and supersession checks against an isolated real graph."""
import os
import unittest
import uuid
from agent.tools import CorridorTools, query_records, run_query
from agent.loop import Investigation
from data.check_company import inspect_company
from data.generate import generate
from data.load import load
from db import connect
from tests.test_agent import ScriptedModel


class CompanyModel(ScriptedModel):
    def __init__(self, override=None):
        super().__init__()
        self.override = override or {}

    def choose(self, context, findings):
        return {'name': 'finish_investigation', 'params': {}}

    def choose_policy(self, company):
        return sorted(p['id'] for p in company[0]['policies'])[0]

    def decide(self, context, findings):
        return super().decide(context, findings) | self.override


@unittest.skipUnless(os.getenv('CORRIDOR_LIVE_TESTS') == '1', 'Requires remote FalkorDB')
class CompanyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old = os.environ.get('GRAPH_NAME')
        os.environ['GRAPH_NAME'] = 'corridor_test_' + uuid.uuid4().hex
        try:
            cls.graph = connect()
        finally:
            if old is None: os.environ.pop('GRAPH_NAME', None)
            else: os.environ['GRAPH_NAME'] = old
        cls.addClassCleanup(cls.graph.delete)
        data, _ = generate(42)
        # Company and one known account suffice; avoid unrelated transaction fixtures.
        labels = {'Team', 'Employee', 'Corridor', 'Policy', 'Doc', 'Decision', 'Case', 'Finding'}
        data['nodes'] = [n for n in data['nodes'] if n['label'] in labels or n['key'] == 'mule_0']
        ids = {n['key'] for n in data['nodes']}
        data['edges'] = [e for e in data['edges'] if e['source'] in ids and e['target'] in ids]
        load(cls.graph, data)
        cls.tools = CorridorTools(cls.graph)

    def state(self, cid):
        return query_records(self.graph, 'case_state', {'case_id': cid})[0]

    def test_context_sources_and_current_precedents(self):
        self.assertEqual(set(inspect_company(self.graph)), {'US-NG', 'NG-US', 'experts'})

    def test_loop_routes_both_corridors(self):
        for corridor, policy, decision, employee in [('US-NG', 'POL-AML-1', 'DEC-6', 'emp_0'),
                                                      ('NG-US', 'POL-AML-5', 'DEC-4', 'emp_1')]:
            loop = Investigation(self.graph, CompanyModel())
            result = loop.run('mule_0', corridor)
            state = self.state(result['case_id'])
            self.assertEqual((state['policy_id'], state['decision_id'], state['assignee_id']),
                             (policy, decision, employee))
            self.assertEqual([f['tool'] for f in loop.findings][-2:], ['corridor_context', 'precedents'])

    def test_invalid_model_grounding_closes_unrouted(self):
        for override in [{'precedent_decision_id': 'DEC-0'}, {'policy_id': 'POL-AML-5'},
                         {'assignee_employee_id': 'emp_1'}, {'precedent_decision_id': 'DEC-4'}]:
            result = Investigation(self.graph, CompanyModel(override)).run('mule_0')
            self.assertEqual((result['verdict'], result['error']), ('MONITOR', 'review_required'))
            state = self.state(result['case_id'])
            self.assertTrue(all(state[k] is None for k in ('policy_id', 'decision_id', 'assignee_id')))

    def test_write_rejects_mismatched_references_without_partial_closure(self):
        cid = self.tools.open_case('mule_0')['case_id']
        args = dict(case_id=cid, verdict='MONITOR', risk=.5, pattern='none', policy_id='POL-AML-1',
                    decision_id='DEC-6', assignee_id='emp_0', members=['mule_0'])
        for change in [{'decision_id': 'DEC-0'}, {'decision_id': 'DEC-4'}, {'assignee_id': 'emp_1'}]:
            with self.assertRaises(ValueError): self.tools.close_case(**(args | change))
            state = self.state(cid)
            self.assertEqual(state['status'], 'open')
            self.assertTrue(all(state[k] is None for k in ('policy_id', 'decision_id', 'assignee_id')))
        self.tools.close_case(**args)
        self.assertEqual(self.state(cid)['status'], 'closed')

    def test_z_supersession_after_retrieval_is_rechecked_at_write(self):
        self.assertEqual(self.tools.precedents('POL-AML-1')[0]['decision'], 'DEC-6')
        cid = self.tools.open_case('mule_0')['case_id']
        run_query(self.graph, 'load_node_Decision', {'rows': [{'props': {
            'id': 'DEC-new', 'summary': 'Synthetic replacement', 'date': 2000000000, 'outcome': 'MONITOR'}}]})
        for query, source, target in [('BASED_ON_Decision_Policy', 'DEC-new', 'POL-AML-1'),
                                      ('MADE_BY_Decision_Employee', 'DEC-new', 'emp_0'),
                                      ('SUPERSEDES_Decision_Decision', 'DEC-new', 'DEC-6')]:
            run_query(self.graph, 'load_edge_' + query, {'rows': [{'source': source, 'target': target, 'props': {}}]})
        self.assertEqual([r['decision'] for r in self.tools.precedents('POL-AML-1')], ['DEC-new'])
        args = dict(case_id=cid, verdict='MONITOR', risk=.5, pattern='none', policy_id='POL-AML-1',
                    decision_id='DEC-6', assignee_id='emp_0', members=['mule_0'])
        with self.assertRaises(ValueError): self.tools.close_case(**args)
        self.assertEqual(self.state(cid)['status'], 'open')
        self.tools.close_case(**(args | {'decision_id': 'DEC-new'}))
        self.assertEqual(self.state(cid)['decision_id'], 'DEC-new')
