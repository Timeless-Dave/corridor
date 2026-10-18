MATCH p=(s:Account)-[:SENT*1..5]->(c:Account {id: $collector})
WHERE s.id IN $sender_ids AND s.id <> c.id
  AND all(n IN nodes(p) WHERE n.id IN $scope_ids)
  AND all(r IN relationships(p) WHERE r.ts >= $since AND r.ts <= $until AND coalesce(r.blocked, false) = false)
RETURN DISTINCT s.id AS sender ORDER BY sender
