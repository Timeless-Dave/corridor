import unittest
from unittest.mock import Mock
from mcp.server.fastmcp.exceptions import ToolError
from agent.tools import READ_TOOLS
from mcp_server.server import create_server


class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_is_read_only_and_lazy(self):
        factory = Mock()
        server = create_server(factory)
        tools = await server.list_tools()
        self.assertEqual({t.name for t in tools}, READ_TOOLS)
        self.assertTrue(all(t.annotations.readOnlyHint for t in tools))
        factory.assert_not_called()

    async def test_bad_parameters_never_reach_database(self):
        factory = Mock()
        server = create_server(factory)
        for name, params in [('circular_flows', {'account_id': 'a', 'max_hops': 6}),
                             ('fan_in', {'account_id':'a', 'since':True, 'max_amount':500}),
                             ('collector_rank', {'account_ids':['a'] * 201})]:
            with self.subTest(name=name), self.assertRaises(ToolError):
                await server.call_tool(name, params)
        factory.assert_not_called()

    async def test_fixed_read_query_and_sanitized_failure(self):
        graph = Mock()
        graph.ro_query.return_value = Mock(header=[[1, 'account']], result_set=[['peer']])
        server = create_server(lambda: graph)
        await server.call_tool('shared_identifiers', {'account_id':'a'})
        self.assertEqual(graph.ro_query.call_args.args[1], {'account_id':'a'})
        graph.query.assert_not_called()
        graph.ro_query.side_effect = RuntimeError('credential-secret')
        with self.assertRaises(ToolError) as error:
            await server.call_tool('shared_identifiers', {'account_id':'a'})
        self.assertNotIn('credential-secret', str(error.exception))
        self.assertIn('FalkorDB unavailable', str(error.exception))

    async def test_writes_and_arbitrary_queries_are_not_callable(self):
        factory = Mock()
        server = create_server(factory)
        for name in ['open_case', 'record_finding', 'close_case', 'run_query', 'reset']:
            with self.subTest(name=name), self.assertRaises(ToolError):
                await server.call_tool(name, {})
        factory.assert_not_called()
