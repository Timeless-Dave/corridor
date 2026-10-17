"""Read-only stdio MCP adapter; all database work stays in agent.tools."""
from typing import Annotated
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field
from agent.schemas import DESCRIPTIONS
from agent.tools import CorridorTools, READ_TOOLS
from db import connect, DatabaseError

Identifier = Annotated[str, Field(strict=True, min_length=1, max_length=256)]
Identifiers = Annotated[list[Identifier], Field(max_length=200)]


def create_server(graph_factory=connect):
    server = FastMCP('Corridor', instructions=(
        'Synthetic payment investigation data. Shared identifiers alone do not establish fraud. '
        'These tools retrieve graph evidence; they do not issue or persist compliance verdicts.'),
        log_level='WARNING')

    def call(name, **params):
        try:
            return CorridorTools(graph_factory()).call(name, **params)
        except DatabaseError:
            raise ToolError('FalkorDB unavailable or query failed; check local connection settings.') from None
        except (ValueError, TypeError):
            raise ToolError('Invalid tool parameters; check the advertised schema and identifier values.') from None
        except Exception:
            raise ToolError('Tool execution failed; inspect local service configuration.') from None

    def shared_identifiers(account_id: Identifier) -> list[dict]:
        return call('shared_identifiers', account_id=account_id)

    def circular_flows(account_id: Identifier, max_hops: Annotated[int, Field(strict=True, ge=2, le=5)] = 5) -> list[dict]:
        return call('circular_flows', account_id=account_id, max_hops=max_hops)

    def fan_in(account_id: Identifier, since: Annotated[int, Field(strict=True, ge=0)],
               max_amount: Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]) -> list[dict]:
        return call('fan_in', account_id=account_id, since=since, max_amount=max_amount)

    def ajo_payout_pattern(pool_id: Identifier) -> list[dict]:
        return call('ajo_payout_pattern', pool_id=pool_id)

    def ring_communities(account_ids: Identifiers) -> list[dict]:
        return call('ring_communities', account_ids=account_ids)

    def connected_cluster(account_id: Identifier) -> list[dict]:
        return call('connected_cluster', account_id=account_id)

    def collector_rank(account_ids: Identifiers) -> list[dict]:
        return call('collector_rank', account_ids=account_ids)

    def link_to_known_bad(account_id: Identifier) -> list[dict]:
        return call('link_to_known_bad', account_id=account_id)

    def corridor_context(corridor_code: Identifier) -> list[dict]:
        return call('corridor_context', corridor_code=corridor_code)

    def precedents(policy_id: Identifier) -> list[dict]:
        return call('precedents', policy_id=policy_id)

    def who_knows(pattern: Identifier) -> list[dict]:
        return call('who_knows', pattern=pattern)

    def prior_cases(account_id: Identifier, exclude_case_id: Annotated[str, Field(strict=True, max_length=256)] = '') -> list[dict]:
        return call('prior_cases', account_id=account_id, exclude_case_id=exclude_case_id)

    descriptions = {**DESCRIPTIONS,
        'corridor_context': 'Retrieve corridor owner, lead, policies and their source documents.',
        'precedents': 'Retrieve current policy precedents and their authors, excluding superseded decisions.',
        'prior_cases': 'Retrieve persisted case memory for an account; exclude the current case if supplied.'}
    functions = [shared_identifiers, circular_flows, fan_in, ajo_payout_pattern,
                 ring_communities, connected_cluster, collector_rank, link_to_known_bad,
                 corridor_context, precedents, who_knows, prior_cases]
    assert {fn.__name__ for fn in functions} == READ_TOOLS
    for fn in functions:
        server.add_tool(fn, description=descriptions[fn.__name__],
                        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                                                    idempotentHint=True, openWorldHint=False))
    return server
