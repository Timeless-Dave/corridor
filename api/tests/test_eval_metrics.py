import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('corridor_eval',Path(__file__).resolve().parents[2]/'eval/run.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class EvaluationMetricsTests(unittest.TestCase):
    def test_unknown_errors_are_not_counted_as_clearances(self):
        rows=[{'expected_ring_member':True,'verdict':'MONITOR'},
              {'expected_ring_member':False,'verdict':'MONITOR'},
              {'expected_ring_member':False,'verdict':'CLEAR'},
              {'expected_ring_member':True,'error':'database_unavailable'}]
        m=module.metrics(rows)
        self.assertEqual((m['tp'],m['fp'],m['tn'],m['fn'],m['errors']),(1,1,1,0,1))
        self.assertEqual(m['precision'],.5)
        self.assertEqual(m['recall'],1)
