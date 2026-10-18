MATCH (a:Account)-[r:SENT]->(b:Account)
WHERE a.id IN $scope_ids AND b.id IN $scope_ids AND a.id <> b.id
  AND r.ts >= $since AND r.ts <= $until AND coalesce(r.blocked, false) = false
WITH DISTINCT a.id AS source, b.id AS target
MATCH (o:FlowNode {id: source, side: 'out'}), (i:FlowNode {id: target, side: 'in'})
CREATE (o)-[:FLOW {cap: 100000.0}]->(i)
RETURN count(*) AS edges
