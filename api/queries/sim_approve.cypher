MATCH (c:Case {id: $case_id})-[:HAS_FREEZE_PLAN]->(p:FreezePlan {id: $plan_id})
WHERE c.status = 'closed' AND c.verdict = 'FREEZE' AND NOT (p)-[:APPROVED_AS]->()
CREATE (o:FreezeOrder {id: $order_id, approved_at: $now, status: 'pending_measurement', freeze_ids: $freeze_ids})
CREATE (p)-[:APPROVED_AS]->(o)
CREATE (c)-[:HAS_FREEZE_ORDER]->(o)
WITH o
UNWIND $freeze_ids AS account_id
MATCH (a:Account {id: account_id})
SET a.frozen = true
WITH DISTINCT o
MATCH (a:Account)-[r:SENT]->(b:Account)
WHERE a.id IN $freeze_ids OR b.id IN $freeze_ids
SET r.blocked = true
RETURN o.id AS order_id, count(r) AS blocked_transfers
