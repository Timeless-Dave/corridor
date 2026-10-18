MATCH (s:FlowNode {side: 'in'}) WHERE s.id IN $sender_ids
WITH collect(s) AS sources
MATCH (t:FlowNode {id: $collector, side: 'out'})
CALL algo.maxFlow({sourceNodes: sources, targetNodes: [t], capacityProperty: 'cap', relationshipTypes: ['FLOW']})
YIELD edges, edgeFlows, maxFlow
RETURN [e IN edges | [startNode(e).id, startNode(e).side, endNode(e).id, endNode(e).side]] AS edges, edgeFlows, maxFlow
