MATCH (c:Case {id: $case_id})
CREATE (p:FreezePlan {id: $plan_id, payload: $payload, created_at: $now, fingerprint: $fingerprint})
CREATE (c)-[:HAS_FREEZE_PLAN]->(p)
RETURN p.id AS plan_id
