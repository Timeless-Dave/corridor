MATCH (:Case {id: $case_id})-[:HAS_FREEZE_ORDER]->(o:FreezeOrder)
OPTIONAL MATCH (o)-[:RECEIPT]->(m:Measurement)
RETURN properties(o) AS order, properties(m) AS measurement ORDER BY o.approved_at DESC
