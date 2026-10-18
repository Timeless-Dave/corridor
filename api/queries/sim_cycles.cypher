MATCH p=(c:Account {id: $collector})-[:SENT*2..5]->(c)
WHERE all(n IN nodes(p) WHERE n.id IN $scope_ids)
  AND all(r IN relationships(p) WHERE r.ts >= $since AND r.ts <= $until AND coalesce(r.blocked, false) = false)
RETURN count(p) AS cycles_remaining
