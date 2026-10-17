MATCH (a:Account {id: $account_id})<-[r:INVOLVES]-(c:Case)
WHERE c.id <> $exclude_case_id
OPTIONAL MATCH (c)-[:HAS_FINDING]->(f:Finding)
WITH c, r, f ORDER BY f.step
RETURN c.id AS case_id, c.verdict AS verdict, c.pattern AS pattern,
       c.opened_at AS opened_at, r.role AS role, collect(f.text)[..3] AS key_findings
ORDER BY opened_at DESC, case_id
