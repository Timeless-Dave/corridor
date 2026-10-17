"""Exercise the real stdio protocol against the configured graph, without writes/model calls."""
import asyncio
import json
import sys
from pathlib import Path
from datetime import timedelta
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from agent.tools import READ_TOOLS


async def verify():
    truth = json.loads((Path(__file__).parent / 'ground_truth.json').read_text())
    calls = {
        'shared_identifiers': {'account_id': 'shared_0'},
        'circular_flows': {'account_id': 'cycle_0', 'max_hops':5},
        'fan_in': {key: truth['rings']['fan_in']['params'][key] for key in ('account_id', 'since', 'max_amount')},
        'ajo_payout_pattern': truth['rings']['ajo']['params'],
        'ring_communities': {'account_ids':['cycle_0','cycle_1']},
        'connected_cluster': {'account_id':'shared_0'},
        'collector_rank': {'account_ids':['collector_0','mule_0']},
        'link_to_known_bad': {'account_id':'collector_0'},
        'corridor_context': {'corridor_code':'US-NG'},
        'precedents': {'policy_id':'POL-AML-1'},
        'who_knows': {'pattern':'fan_in_mule'},
        'prior_cases': {'account_id':'mule_0'},
    }
    params = StdioServerParameters(command=sys.executable, args=['-m','mcp_server'],
                                   cwd=str(Path(__file__).resolve().parents[1]))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=90)) as session:
            initialization = await session.initialize()
            listed = await session.list_tools()
            assert {t.name for t in listed.tools} == READ_TOOLS
            results = {}
            for name, arguments in calls.items():
                result = await session.call_tool(name, arguments)
                assert not result.isError, f'{name} returned a tool error'
                assert result.structuredContent is not None, f'{name} missing structured data'
                assert result.structuredContent.get('result'), f'{name} returned no seeded evidence'
                results[name] = result.structuredContent
                print(f'Passed: {name}', file=sys.stderr, flush=True)
            assert results['fan_in']['result'][0]['senders'] == 12
            assert any(len(row['transfers']) == 5 for row in results['circular_flows']['result'])
            assert results['corridor_context']['result'][0]['lead_id'] == 'emp_0'
            assert results['precedents']['result'][0]['decision'] == 'DEC-6'
            for name, arguments in [('close_case',{}), ('circular_flows',{'account_id':'cycle_0','max_hops':99})]:
                result = await session.call_tool(name, arguments)
                assert result.isError, f'{name} should have been rejected'
            return {'verified':True, 'protocol_version':initialization.protocolVersion,
                    'tool_count':len(listed.tools), 'results':results,
                    'rejected':['unexposed write','invalid hop limit'], 'model_calls':0, 'graph_writes':0}


if __name__ == '__main__':
    report = asyncio.run(verify())
    (Path(__file__).resolve().parents[2] / 'docs/m8-live-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'verified':True,'tools':report['tool_count']}))
