MATCH (a:Account {id: $account_id})
CREATE (c:Case {id: $case_id, status: 'open', opened_at: $now, requested_account_id: $account_id})
CREATE (c)-[:INVOLVES {role: 'flagged'}]->(a)
RETURN c.id AS case_id, true AS account_exists
UNION ALL
OPTIONAL MATCH (a:Account {id: $account_id})
WITH a WHERE a IS NULL
CREATE (c:Case {id: $case_id, status: 'open', opened_at: $now, requested_account_id: $account_id})
RETURN c.id AS case_id, false AS account_exists
