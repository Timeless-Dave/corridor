MATCH (c:Case {id: $case_id})
OPTIONAL MATCH (c)-[:APPLIED]->(p:Policy)
OPTIONAL MATCH (c)-[:PRECEDENT]->(d:Decision)
OPTIONAL MATCH (c)-[:ASSIGNED_TO]->(e:Employee)
OPTIONAL MATCH (c)-[r:INVOLVES]->(a:Account)
RETURN c.status AS status, c.verdict AS verdict, c.risk AS risk, p.id AS policy_id,
       d.id AS decision_id, e.id AS assignee_id, collect({id:a.id, role:r.role}) AS members
