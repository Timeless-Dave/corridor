import os
import unittest
from unittest.mock import patch
from db import connect, DatabaseError
from agent.tools import run_query


class ConnectionTests(unittest.TestCase):
    def test_tls_and_timeouts(self):
        with patch.dict(os.environ, {'FALKORDB_HOST':'test.invalid', 'FALKORDB_TLS':'true',
                                     'FALKORDB_PASSWORD':'private-value'}, clear=True), \
             patch('dotenv.load_dotenv'), patch('falkordb.FalkorDB') as client:
            connect()
            kwargs = client.call_args.kwargs
            self.assertTrue(kwargs['ssl'])
            self.assertTrue(kwargs['ssl_check_hostname'])
            self.assertEqual(kwargs['ssl_cert_reqs'], 'required')
            self.assertEqual(kwargs['socket_connect_timeout'], 10)
            self.assertEqual(kwargs['retry'].get_retries(), 0)
            client.return_value.select_graph.assert_called_once_with('corridor')

    def test_missing_host(self):
        with patch.dict(os.environ, {}, clear=True), patch('dotenv.load_dotenv'):
            with self.assertRaisesRegex(DatabaseError, 'Set FALKORDB_HOST'):
                connect()

    def test_errors_do_not_expose_credentials(self):
        class BrokenGraph:
            def ro_query(self, *args):
                raise RuntimeError('password=private-value')
        with self.assertRaises(DatabaseError) as error:
            run_query(BrokenGraph(), 'count_nodes', readonly=True)
        self.assertNotIn('private-value', str(error.exception))
        self.assertTrue(error.exception.__suppress_context__)

if __name__ == '__main__':
    unittest.main()
