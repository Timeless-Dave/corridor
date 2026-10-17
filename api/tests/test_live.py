"""Opt-in integration tests create and delete only a unique disposable graph."""
import os
import unittest
import uuid
import sys
from collections import Counter
from data.generate import generate
from data.load import load
from data.verify import verify
from db import connect, DatabaseError
from agent.tools import run_query


@unittest.skipUnless(os.getenv('CORRIDOR_LIVE_TESTS') == '1', 'Remote integration tests require CORRIDOR_LIVE_TESTS=1 and .env')
class LiveTests(unittest.TestCase):
    def test_round_trip(self):
        previous = os.environ.get('GRAPH_NAME')
        name = 'corridor_test_' + uuid.uuid4().hex
        os.environ['GRAPH_NAME'] = name
        graph = None
        try:
            graph = connect()
            print('Connected; loading disposable graph.', flush=True)
            data, truth = generate(42)
            first = load(graph, data)
            print('Initial load complete; verifying evidence.', flush=True)
            self.assertEqual(dict(first['nodes']), dict(Counter(n['label'] for n in data['nodes'])))
            self.assertEqual(dict(first['edges']), dict(Counter(e['type'] for e in data['edges'])))
            verify(graph, truth)
            self.assertEqual(run_query(graph, 'company_owners', readonly=True),
                             [['NG-US','team_1','emp_1'], ['US-NG','team_0','emp_0']])
            self.assertEqual(run_query(graph, 'current_precedents', {'policy_id':'POL-AML-1'}, readonly=True), [['DEC-6']])
            self.assertEqual(run_query(graph, 'seed_history', {'account_id':'mule_0'}, readonly=True),
                             [['case_history','FREEZE','flagged','finding_history']])
            indexes = run_query(graph, 'indexes', readonly=True)
            self.assertEqual({row[0] for row in indexes}, {'Account','Device','Phone','Case','Corridor','Policy'})
            with self.assertRaisesRegex(ValueError, 'populated'):
                load(graph, data)
            print('Proofs passed; testing reset and reload.', flush=True)
            self.assertEqual(load(graph, data, reset=True), first)
            verify(graph, truth)
            print('Reset/reload and repeated proofs passed.', flush=True)
        finally:
            had_error = sys.exc_info()[0] is not None
            cleanup_failed = False
            if graph is not None:
                try:
                    if name in graph.client.list_graphs():
                        graph.delete()
                except Exception:
                    cleanup_failed = True
                    print(f'Cleanup failed for disposable graph {name}; original failure preserved.', flush=True)
            if previous is None:
                os.environ.pop('GRAPH_NAME', None)
            else:
                os.environ['GRAPH_NAME'] = previous
            if cleanup_failed and not had_error:
                raise DatabaseError('Disposable test graph cleanup failed.') from None

if __name__ == '__main__':
    unittest.main()
