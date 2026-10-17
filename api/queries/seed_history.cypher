MATCH (c:Case)-[r:INVOLVES]->(a:Account {id: $account_id})
MATCH (c)-[:HAS_FINDING]->(f:Finding)-[:CITES]->(a)
RETURN c.id, c.verdict, r.role, f.id
