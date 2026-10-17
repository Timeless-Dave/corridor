MATCH (a:Account {id: $account_id})
OPTIONAL MATCH (a)-[:MEMBER_OF]->(pool:AjoPool)
WITH a, collect(DISTINCT pool.id) AS pool_ids
OPTIONAL MATCH (a)-[t:SENT]-(other:Account)
RETURN a.id AS account_id, a.country AS country, pool_ids, max(t.ts) AS latest_transfer_ts
