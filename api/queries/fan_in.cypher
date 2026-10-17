MATCH (c:Account {id: $account_id})
OPTIONAL MATCH (s:Account)-[t:SENT]->(c)
WHERE t.ts > $since AND t.ts <= $since + 172800 AND t.amount < $max_amount
RETURN c.id AS collector, count(DISTINCT s) AS senders, coalesce(sum(t.amount), 0) AS total,
       collect(DISTINCT s.id) AS sender_ids, collect(t.id) AS transfers,
       min(t.ts) AS first_ts, max(t.ts) AS last_ts
