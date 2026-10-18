MATCH (c:Case {id: $case_id})
OPTIONAL MATCH (c)-[:HAS_FINDING]->(:Finding)-[:CITES]->(a:Account)
RETURN c.requested_account_id AS collector, collect(DISTINCT a.id) AS accounts
