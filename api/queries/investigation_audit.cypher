MATCH (c:Case {id: $case_id})
OPTIONAL MATCH (c)-[:HAS_FINDING]->(f:Finding)
WITH c, f ORDER BY f.step
RETURN properties(c) AS case, collect(DISTINCT properties(f)) AS findings
