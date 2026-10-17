MATCH (d:Decision)-[:BASED_ON]->(:Policy {id: $policy_id})
WHERE NOT (:Decision)-[:SUPERSEDES]->(d)
RETURN d.id ORDER BY d.id
