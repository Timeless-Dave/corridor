UNWIND $scope_ids AS account_id
CREATE (i:FlowNode {id: account_id, side: 'in'}), (o:FlowNode {id: account_id, side: 'out'}),
       (i)-[:FLOW {cap: CASE WHEN account_id IN $candidate_ids THEN 1.0 ELSE 100000.0 END}]->(o)
RETURN count(*) AS nodes
