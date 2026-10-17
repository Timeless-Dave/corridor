MATCH (c:Case {id: $case_id})-[:HAS_FINDING]->(:Finding)-[:CITES]->(n)
RETURN DISTINCT coalesce(n.id, n.fingerprint, n.number, n.code) AS id,
       labels(n) AS labels, properties(n) AS properties
ORDER BY id LIMIT 500
