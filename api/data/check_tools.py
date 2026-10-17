"""Read-only M2 smoke test against the configured demo graph."""
import json
from agent.tools import CorridorTools
from data.generate import DATA_DIR
from db import connect, DatabaseError


def inspect_tools(graph):
    t = json.loads((DATA_DIR/'ground_truth.json').read_text())
    tool = CorridorTools(graph)
    return {
        'shared_identifiers': tool.shared_identifiers('cycle_0'),
        'circular_flows': tool.circular_flows('cycle_0'),
        'fan_in': tool.fan_in('collector_0', t['reference_ts']-1, 500),
        'ajo_payout_pattern': tool.ajo_payout_pattern('pool_abuse'),
        'ring_communities': tool.ring_communities(t['rings']['cycle']['accounts']),
        'connected_cluster': tool.connected_cluster('cycle_0'),
        'collector_rank': tool.collector_rank(t['rings']['fan_in']['accounts']),
        'link_to_known_bad': tool.link_to_known_bad('mule_1'),
        'corridor_context': tool.corridor_context('US-NG'),
        'precedents': tool.precedents('POL-AML-1'),
        'who_knows': tool.who_knows('fan_in_mule'),
        'prior_cases': tool.prior_cases('mule_0'),
    }


def main():
    try:
        print(json.dumps(inspect_tools(connect()), indent=2, allow_nan=False))
    except DatabaseError as e:
        print(str(e))
        raise SystemExit(1)

if __name__ == '__main__':
    main()
