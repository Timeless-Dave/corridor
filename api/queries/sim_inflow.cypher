MATCH (s:Account)-[r:SENT]->(c:Account {id: $collector})
WHERE s.id IN $scope_ids AND r.ts >= $since AND r.ts <= $until AND coalesce(r.blocked, false) = false
RETURN count(r) AS transfers, coalesce(sum(r.amount), 0) AS inflow_volume
