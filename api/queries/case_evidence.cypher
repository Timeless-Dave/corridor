MATCH (c:Case {id: $case_id})-[:HAS_FINDING]->(f:Finding)
OPTIONAL MATCH (f)-[:CITES]->(n)
RETURN f.id AS finding_id, f.step AS step, f.tool AS tool, f.query_name AS query_name,
       f.params AS params, f.text AS text, collect(DISTINCT coalesce(n.id, n.fingerprint, n.number)) AS cited
ORDER BY step, finding_id
