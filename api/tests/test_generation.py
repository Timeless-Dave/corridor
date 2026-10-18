import copy
import unittest
from collections import Counter
from data.generate import generate, BASE_TS
from data.load import validate, load
from agent.tools import QUERIES


class GenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.truth = generate(42)

    def test_reproducibility(self):
        self.assertEqual((self.data, self.truth), generate(42))
        self.assertNotEqual(self.data, generate(43)[0])

    def test_identifiers_and_references(self):
        validate(self.data)
        broken = copy.deepcopy(self.data)
        broken['edges'][0]['target'] = 'missing'
        with self.assertRaises(ValueError):
            validate(broken)
        broken = copy.deepcopy(self.data)
        broken['nodes'].append(broken['nodes'][0])
        with self.assertRaises(ValueError):
            validate(broken)

    def test_counts_and_overlap(self):
        counts = Counter(n['label'] for n in self.data['nodes'])
        self.assertEqual({k:counts[k] for k in ('Account','AjoPool','Team','Employee','Corridor','Policy','Doc','Decision','Case')},
                         dict(Account=2062, AjoPool=33, Team=3, Employee=12, Corridor=2, Policy=6, Doc=6, Decision=8, Case=1))
        cycle = set(self.truth['rings']['cycle']['accounts'])
        cluster = set(self.truth['rings']['shared']['accounts'])
        self.assertEqual(cycle & cluster, {'cycle_0', 'cycle_1'})
        background = [e for e in self.data['edges'] if e['type']=='SENT' and 'pool_id' not in e['props']
                      and e['source'].startswith('acct_')]
        self.assertEqual(len(background), 20000)

    def test_cycle_and_fan_in(self):
        edges = {e['props']['id']:e for e in self.data['edges'] if e['type']=='SENT'}
        cycle = [edges[k] for k in self.truth['rings']['cycle']['transfers']]
        self.assertEqual(len(cycle), 5)
        for a,b in zip(cycle, cycle[1:]):
            self.assertEqual(a['target'], b['source'])
            self.assertLess(a['props']['ts'], b['props']['ts'])
            self.assertGreater(a['props']['amount'], b['props']['amount'])
        self.assertEqual(cycle[-1]['target'], cycle[0]['source'])
        self.assertLessEqual(cycle[-1]['props']['ts']-cycle[0]['props']['ts'], 72*3600)
        fan = [e for e in edges.values() if e['target']=='collector_0']
        self.assertEqual(len({e['source'] for e in fan}), 12)
        self.assertTrue(all(e['props']['amount']<500 and BASE_TS<=e['props']['ts']<=BASE_TS+48*3600 for e in fan))

    def test_payout_rounds(self):
        for i in range(30):
            payouts = [e for e in self.data['edges'] if e['props'].get('pool_id')==f'pool_{i:02d}']
            self.assertEqual(len({e['target'] for e in payouts}), 3)
        bad = [e for e in self.data['edges'] if e['props'].get('pool_id')=='pool_abuse']
        self.assertEqual({e['target'] for e in bad}, {'ajo_0'})
        self.assertEqual({e['props']['round'] for e in bad}, {0,1,2})

    def test_eight_decoys_are_labeled_only_outside_graph(self):
        decoys=self.truth['decoys']
        self.assertEqual(len(decoys),8)
        self.assertEqual(len({d['account_id'] for d in decoys}),8)
        self.assertEqual(len(self.truth['evaluation_flags']),12)
        planted={a for ring in self.truth['rings'].values() for a in ring['accounts']}
        self.assertFalse(planted & {a for d in decoys for a in d['members']})
        self.assertEqual(sum(n['props'].get('flagged',False) for n in self.data['nodes']),12)

    def test_ground_truth_not_stored(self):
        for n in self.data['nodes']:
            self.assertFalse({'ring', 'ground_truth', 'is_fraud'} & n['props'].keys())

    def test_loader_refuses_populated_graph(self):
        class Result:
            result_set = [[1]]
        class Client:
            def list_graphs(self):
                return ['test']
        class Graph:
            name = 'test'
            client = Client()
            def ro_query(self, *args):
                return Result()
            def query(self, *args):
                raise AssertionError('Must not write to populated graph')
        with self.assertRaisesRegex(ValueError, 'populated'):
            load(Graph(), self.data)

    def test_query_registry(self):
        for pattern in self.truth['rings']:
            self.assertIn(f'proof_{pattern}', QUERIES)
        self.assertEqual(sum(k.startswith('index_') for k in QUERIES), 6)

if __name__ == '__main__':
    unittest.main()
