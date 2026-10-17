MATCH (c:Case {pattern: $pattern})-[:PRECEDENT]->(d:Decision)-[:MADE_BY]->(e:Employee)
RETURN e.id AS employee_id, e.name AS employee, e.role AS role, count(DISTINCT c) AS cases
ORDER BY cases DESC, employee_id LIMIT 5
