"""M2 contracts and live query behavior on a disposable seeded graph."""
import json
import math
import os
import unittest
import uuid
from unittest.mock import Mock
from agent.tools import CorridorTools, TOOL_NAMES, query_records
from data.generate import generate, BASE_TS
from data.load import load
from db import connect, DatabaseError


class ToolContractTests(unittest.TestCase):
    def setUp(self):
        self.graph = Mock()
        self.tools = CorridorTools(self.graph)

    def test_dispatch_excludes_arbitrary_queries_and_ingestion(self):
        self.assertEqual(len(TOOL_NAMES), 15)
        for name in ('run_query','load_node_Account','_write','__init__'):
            with self.assertRaises(ValueError):
                self.tools.call(name)
        self.graph.query.assert_not_called()

    def test_bounds_and_invalid_values(self):
        for hops in (1,6,2.5,True):
            with self.assertRaises(ValueError):
                self.tools.circular_flows('cycle_0',hops)
        for amount in (-1,0,float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):
                self.tools.fan_in('collector_0',BASE_TS,amount)
        with self.assertRaises(ValueError):
            self.tools.collector_rank(['x']*201)
        self.assertEqual(self.tools.collector_rank([]),[])
        self.graph.ro_query.assert_not_called()

    def test_parameters_remain_data(self):
        self.graph.ro_query.return_value.header=[]
        self.graph.ro_query.return_value.result_set=[]
        attack="x'}) DELETE n //"
        self.tools.shared_identifiers(attack)
        query, params = self.graph.ro_query.call_args.args
        self.assertNotIn(attack,query)
        self.assertEqual(params,{'account_id':attack})

    def test_invalid_write_inputs_never_reach_database(self):
        for risk in (float('nan'),float('inf'),-1,2,True):
            with self.assertRaises(ValueError):
                self.tools.close_case('c','MONITOR',risk,'none','p','d','e',['a'])
        with self.assertRaises(ValueError):
            self.tools.record_finding('c',1,'text','unknown',{},[])
        self.graph.query.assert_not_called()


@unittest.skipUnless(os.getenv('CORRIDOR_LIVE_TESTS')=='1', 'Requires CORRIDOR_LIVE_TESTS=1 and remote .env')
class QueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name='corridor_test_'+uuid.uuid4().hex
        previous=os.environ.get('GRAPH_NAME')
        os.environ['GRAPH_NAME']=name
        try:
            cls.graph=connect()
        finally:
            if previous is None:
                os.environ.pop('GRAPH_NAME',None)
            else:
                os.environ['GRAPH_NAME']=previous
        cls.addClassCleanup(cls.cleanup_graph)
        data,cls.truth=generate(42)
        def account(key):
            data['nodes'].append({'label':'Account','key':key,'props':{'id':key,'kyc_tier':2}})
        def sent(a,b,key,amount,ts):
            data['edges'].append({'type':'SENT','source':a,'target':b,
                                 'props':{'id':key,'amount':amount,'ts':ts,'currency':'USD'}})
        for hops in (2,3,4):
            ids=[f'test_cycle_{hops}_{i}' for i in range(hops)]
            for key in ids:
                account(key)
            for i,key in enumerate(ids):
                sent(key,ids[(i+1)%hops],f'test_transfer_{hops}_{i}',100-i,BASE_TS+i)
        # Explicit negative cycles: chronology, amount ordering, and time span.
        for kind,amounts,times in [('time',[100,90],[BASE_TS+1,BASE_TS]),
                                  ('amount',[90,100],[BASE_TS,BASE_TS+1]),
                                  ('span',[100,90],[BASE_TS,BASE_TS+259201])]:
            for i in range(2): account(f'invalid_{kind}_{i}')
            for i in range(2):
                sent(f'invalid_{kind}_{i}',f'invalid_{kind}_{1-i}',f'invalid_tx_{kind}_{i}',amounts[i],times[i])
        previous='mule_0'
        for i in range(1,8):
            key=f'path_{i}'
            account(key)
            sent(previous,key,f'path_transfer_{i}',10,BASE_TS)
            previous=key
        for label, prop, relation in (('Device','fingerprint','USED'), ('Phone','number','REGISTERED')):
            identifier = 'test_identifier_' + label
            peer = 'identifier_peer_' + label
            account(peer)
            data['nodes'].append({'label':label,'key':identifier,'props':{prop:identifier}})
            for source in ('mule_0',peer):
                data['edges'].append({'type':relation,'source':source,'target':identifier,'props':{}})
        print('Loading isolated M2 query fixtures.',flush=True)
        load(cls.graph,data)
        cls.tools=CorridorTools(cls.graph)

    @classmethod
    def cleanup_graph(cls):
        try:
            if cls.graph.name in cls.graph.client.list_graphs():
                cls.graph.delete()
        except Exception:
            raise DatabaseError('M2 test graph cleanup failed.') from None

    def test_circular_bounds_order_and_negative_controls(self):
        for hops in (2,3,4):
            key=f'test_cycle_{hops}_0'
            rows=self.tools.circular_flows(key,hops)
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['accounts'],[f'test_cycle_{hops}_{i}' for i in range(hops)]+[key])
            self.assertEqual(rows[0]['timestamps'],[BASE_TS+i for i in range(hops)])
            if hops>2:
                self.assertEqual(self.tools.circular_flows(key,hops-1),[])
        row=self.tools.circular_flows('cycle_0')[0]
        self.assertEqual(row['transfers'],self.truth['rings']['cycle']['transfers'])
        self.assertEqual(row['amounts'],[480,475,470,465,460])
        self.assertEqual(row['volume'],2350)
        self.assertEqual(self.tools.circular_flows('cycle_0',4),[])
        for kind in ('time','amount','span'):
            self.assertEqual(self.tools.circular_flows(f'invalid_{kind}_0'),[])

    def test_fan_in_window_and_threshold(self):
        row=self.tools.fan_in('collector_0',BASE_TS-1,500)[0]
        self.assertEqual(row['senders'],12)
        self.assertEqual(row['total'],4866)
        self.assertEqual(len(row['transfers']),12)
        self.assertEqual(self.tools.fan_in('collector_0',BASE_TS-1,400)[0]['senders'],0)
        self.assertEqual(self.tools.fan_in('collector_0',BASE_TS+172800,500)[0]['senders'],0)
        self.assertEqual(self.tools.fan_in('collector_0',BASE_TS-172801,500)[0]['senders'],0)

    def test_shared_identifiers_and_wcc(self):
        peers={r['account'] for r in self.tools.shared_identifiers('cycle_0')}
        self.assertEqual(peers,set(self.truth['rings']['shared']['accounts'])-{'cycle_0'})
        component=self.tools.connected_cluster('cycle_0')[0]
        self.assertEqual(component['size'],14)
        self.assertTrue(set(self.truth['rings']['shared']['accounts'])<=set(component['members']))
        self.assertNotIn('cycle_2',component['members']) # SENT edges excluded
        self.assertEqual({r['account'] for r in self.tools.shared_identifiers('acct_0000')},{'acct_0001'})

    def test_ajo_rounds_and_legitimate_pool(self):
        rows=self.tools.ajo_payout_pattern('pool_abuse')
        self.assertEqual([(r['first_round'],r['next_round']) for r in rows],[(0,1),(1,2)])
        self.assertTrue(all(r['member']=='ajo_0' and len(r['contributors'])==4 and r['shared_devices']==['ajo_device'] for r in rows))
        self.assertEqual(self.tools.ajo_payout_pattern('pool_00'),[])

    def test_algorithms_filter_and_collector(self):
        ids=self.truth['rings']['fan_in']['accounts']
        rank=self.tools.collector_rank(ids)
        self.assertEqual(rank[0]['account'],'collector_0')
        self.assertEqual({r['account'] for r in rank},set(ids))
        self.assertTrue(all(math.isfinite(r['score']) and r['score']>0 for r in rank))
        requested=self.truth['rings']['cycle']['accounts']
        communities=self.tools.ring_communities(requested)
        members=[m for r in communities for m in r['members']]
        self.assertEqual(set(members),set(requested))
        self.assertEqual(len(members),len(requested)) # IDs may vary, membership coverage must not

    def test_shortest_paths_both_directions_and_bound(self):
        row=self.tools.link_to_known_bad('mule_1')[0]
        self.assertEqual(row['path'],['mule_1','collector_0','mule_0'])
        self.assertEqual(row['hops'],2)
        self.assertEqual(len(row['edge_ids']),2)
        row=self.tools.link_to_known_bad('path_6')[0]
        self.assertEqual(row['hops'],6)
        self.assertEqual(row['path'][0],'path_6')
        self.assertEqual(row['path'][-1],'mule_0')
        self.assertEqual(self.tools.link_to_known_bad('path_7'),[])
        self.assertEqual(self.tools.link_to_known_bad('cycle_0'),[])
        for label in ('Device','Phone'):
            peer='identifier_peer_'+label
            row=self.tools.link_to_known_bad(peer)[0]
            self.assertEqual(row['path'],[peer,'test_identifier_'+label,'mule_0'])
            self.assertEqual(row['hops'],2)

    def test_company_context_and_seeded_memory(self):
        context=self.tools.corridor_context('US-NG')[0]
        self.assertEqual(context['lead_id'],'emp_0')
        self.assertEqual(context['team_id'],'team_0')
        self.assertEqual(len(context['policies']),4)
        self.assertTrue(all(p['source_id'] for p in context['policies']))
        self.assertEqual([r['decision'] for r in self.tools.precedents('POL-AML-1')],['DEC-6'])
        self.assertEqual(self.tools.who_knows('fan_in_mule')[0]['employee_id'],'emp_6')
        self.assertEqual(self.tools.prior_cases('mule_0')[0]['case_id'],'case_history')

    def test_unknown_ids_and_injection_are_empty(self):
        for method in ('shared_identifiers','circular_flows','connected_cluster','link_to_known_bad','prior_cases'):
            self.assertEqual(getattr(self.tools,method)("missing'}) DELETE n //"),[])
        self.assertEqual(self.tools.corridor_context('missing'),[])
        self.assertEqual(self.tools.precedents('missing'),[])
        self.assertEqual(self.tools.ajo_payout_pattern('missing'),[])

    def test_case_finding_and_closure(self):
        case=self.tools.open_case('cycle_0')
        self.assertTrue(case['account_exists'])
        cid=case['case_id']
        self.assertFalse(any(r['case_id']==cid for r in self.tools.prior_cases('cycle_0',cid)))
        cited=['cycle_0','shared_device_0','shared_phone_0','POL-AML-1','DEC-6']
        self.tools.record_finding(cid,1,'Synthetic evidence','shared_identifiers',{'account_id':'cycle_0'},cited+cited[:1])
        self.tools.record_finding(cid,2,'No more evidence','fan_in',{'since':BASE_TS},[])
        evidence=query_records(self.graph,'case_evidence',{'case_id':cid})
        self.assertEqual(len(evidence),2)
        self.assertEqual(set(evidence[0]['cited']),set(cited))
        self.assertEqual(evidence[1]['cited'],[])
        self.assertEqual(json.loads(evidence[0]['params']),{'account_id':'cycle_0'})
        self.assertEqual(evidence[0]['query_name'],'shared_identifiers')
        with self.assertRaises(ValueError):
            self.tools.record_finding(cid,3,'Bad citation','fan_in',{},['cycle_0','missing'])
        self.assertEqual(len(query_records(self.graph,'case_evidence',{'case_id':cid})),2)
        args=dict(case_id=cid,verdict='MONITOR',risk=.5,pattern='circular_layering',
                  policy_id='POL-AML-1',decision_id='DEC-6',assignee_id='emp_0',members=['cycle_0','cycle_1'])
        for change in ({'decision_id':'DEC-0'},{'assignee_id':'emp_1'},{'members':['cycle_0','missing']}):
            with self.assertRaises(ValueError):
                self.tools.close_case(**(args|change))
            self.assertEqual(query_records(self.graph,'case_state',{'case_id':cid})[0]['status'],'open')
        self.tools.close_case(**args)
        state=query_records(self.graph,'case_state',{'case_id':cid})[0]
        self.assertEqual((state['status'],state['verdict'],state['policy_id'],state['decision_id'],state['assignee_id']),
                         ('closed','MONITOR','POL-AML-1','DEC-6','emp_0'))
        self.assertEqual({m['id']:m['role'] for m in state['members']},{'cycle_0':'flagged','cycle_1':'member'})
        with self.assertRaises(ValueError): self.tools.close_case(**args)
        with self.assertRaises(ValueError): self.tools.record_finding(cid,3,'Late','fan_in',{},[])

    def test_unknown_account_case_receipt(self):
        receipt=self.tools.open_case('unknown_account')
        self.assertFalse(receipt['account_exists'])
        self.assertEqual(query_records(self.graph,'case_state',{'case_id':receipt['case_id']})[0]['status'],'open')

if __name__=='__main__':
    unittest.main()
