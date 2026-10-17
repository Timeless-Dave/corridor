MATCH (d:Decision)-[:BASED_ON]->(:Policy {id: $policy_id})
WHERE NOT (:Decision)-[:SUPERSEDES]->(d)
MATCH (d)-[:MADE_BY]->(e:Employee)
RETURN d.id AS decision, d.summary AS summary, d.outcome AS outcome,
       d.date AS date, e.id AS decided_by_id, e.name AS decided_by
ORDER BY date DESC, decision
