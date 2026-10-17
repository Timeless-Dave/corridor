MATCH (s:Account)-[t:SENT]->(c:Account {id: $account_id})
WHERE s.kyc_tier = 1 AND t.ts > $since AND t.ts <= $until AND t.amount < $max_amount
WITH c, count(DISTINCT s) AS senders, collect(DISTINCT s.id) AS sender_ids,
     collect(t.id) AS transfers, sum(t.amount) AS total, min(t.ts) AS first_ts, max(t.ts) AS last_ts
WHERE senders >= 12 AND last_ts - first_ts <= 172800
RETURN c.id AS collector, senders, sender_ids, transfers, total, first_ts, last_ts
