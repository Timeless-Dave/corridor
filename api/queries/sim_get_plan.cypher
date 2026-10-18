MATCH (c:Case {id: $case_id})-[:HAS_FREEZE_PLAN]->(p:FreezePlan)
WHERE $plan_id = '' OR p.id = $plan_id
RETURN p.id AS plan_id, p.payload AS payload, p.created_at AS created_at
ORDER BY created_at DESC, plan_id DESC LIMIT 1
