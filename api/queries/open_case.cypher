OPTIONAL MATCH (a:Account {id: $account_id})
CREATE (c:Case {id: $case_id, status: 'open', opened_at: $now, requested_account_id: $account_id})
FOREACH (_ IN CASE WHEN a IS NULL THEN [] ELSE [1] END | CREATE (c)-[:INVOLVES {role: 'flagged'}]->(a))
RETURN c.id AS case_id, a IS NOT NULL AS account_exists
