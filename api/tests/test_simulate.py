import os
import unittest
import uuid
from unittest.mock import Mock, patch
from agent.simulate import copy_graph, plan, approve, measure, get_plan
from agent.tools import CorridorTools, query_records
from data.generate import generate
from data.load import load
from db import connect, DatabaseError


class ScratchTests(unittest.TestCase):
    def test_cleanup_even_when_measurement_fails(self):
        graph=Mock(); graph.name='test'; clone=graph.copy.return_value
        with self.assertRaises(DatabaseError):
            with copy_graph(graph, 'untrusted/name'):
                raise RuntimeError('failure')
        clone.delete.assert_called_once()
        self.assertTrue(graph.copy.call_args.args[0].startswith('test_sim_'))
        self.assertNotIn('untrusted', graph.copy.call_args.args[0])

    def test_cleanup_failure_is_not_success(self):
        graph=Mock(); graph.name='test'; graph.copy.return_value.delete.side_effect=RuntimeError()
        with self.assertRaisesRegex(DatabaseError,'cleanup'):
            with copy_graph(graph,'case'): pass


@unittest.skipUnless(os.getenv('CORRIDOR_LIVE_TESTS')=='1','Requires remote FalkorDB')
class SimulationLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name='corridor_impact_test_'+uuid.uuid4().hex
        with patch.dict(os.environ,{'GRAPH_NAME':name}): cls.base=connect()
        cls.addClassCleanup(cls.base.delete)
        data,_=generate(42); load(cls.base,data)

    def setUp(self):
        self.graph=self.base.copy(self.base.name+'_case_'+uuid.uuid4().hex)
        self.addCleanup(self.graph.delete)

    def scratch_keys(self):
        return {n for n in self.graph.client.list_graphs() if n.startswith(self.graph.name+'_sim_')}

    def seed_case(self):
        tools=CorridorTools(self.graph)
        cid=tools.open_case('collector_0')['case_id']
        ids=['collector_0']+['mule_'+str(i) for i in range(12)]
        tools.record_finding(cid,1,'Test evidence, not a live model result.','fan_in',{},ids,result=[{'senders':12}])
        tools.record_finding(cid,2,'Test corroboration.','link_to_known_bad',{},ids,result=[{'hops':1}])
        return tools,cid,ids

    def test_counterfactual_cleanup_and_measured_approval(self):
        tools,cid,ids=self.seed_case()
        keys=self.scratch_keys()
        result=plan(self.graph,cid,ids)[0]
        self.assertEqual(self.scratch_keys(),keys)
        self.assertEqual(result['before']['senders_reaching_collector'],12)
        self.assertEqual(result['after']['senders_reaching_collector'],0)
        self.assertEqual((result['min_cut']['accounts'],result['min_cut']['max_flow'],result['min_cut']['verified']),(['collector_0'],1.0,True))
        self.assertEqual(measure(self.graph,result['params']),result['before'])
        self.assertEqual(get_plan(self.graph,cid)['plan_id'],result['plan_id'])
        with self.assertRaisesRegex(ValueError,'closed FREEZE'): approve(self.graph,cid,result['plan_id'])
        tools.close_case(cid,'FREEZE',.8,'fan_in_mule','POL-AML-1','DEC-6','emp_0',ids)
        receipt=approve(self.graph,cid,result['plan_id'])
        self.assertTrue(receipt['matched_projection'])
        self.assertEqual(receipt['after']['senders_reaching_collector'],0)
        orders=query_records(self.graph,'sim_orders',{'case_id':cid})
        self.assertEqual(orders[0]['order']['status'],'measured')
        with self.assertRaises(ValueError): approve(self.graph,cid,result['plan_id'])
        print('LIVE impact:',receipt,flush=True)

    def test_unobserved_candidate_rejected(self):
        _,cid,_=self.seed_case()
        with self.assertRaisesRegex(ValueError,'cited'): plan(self.graph,cid,['unobserved_account'])

    def test_partial_freeze_and_stale_plan_rejection(self):
        tools,cid,ids=self.seed_case()
        partial=plan(self.graph,cid,ids,freeze_ids=['mule_0'])[0]
        self.assertEqual(partial['after']['senders_reaching_collector'],11)
        full=plan(self.graph,cid,ids)[0]
        tools.close_case(cid,'FREEZE',.8,'fan_in_mule','POL-AML-1','DEC-6','emp_0',ids)
        tools2,cid2,_=self.seed_case()
        competing=plan(self.graph,cid2,ids)[0]
        tools2.close_case(cid2,'FREEZE',.8,'fan_in_mule','POL-AML-1','DEC-6','emp_0',ids)
        approve(self.graph,cid,partial['plan_id'])
        with self.assertRaisesRegex(ValueError,'Graph changed'):
            approve(self.graph,cid2,competing['plan_id'])
        self.assertEqual(self.scratch_keys(),set())
