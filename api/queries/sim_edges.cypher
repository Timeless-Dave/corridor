MATCH (a:Account)-[r:SENT]->(b:Account)
WHERE (a.id IN $account_ids OR b.id IN $account_ids)
  AND r.ts >= $since AND r.ts <= $until
RETURN a.id AS source, b.id AS target, r.id AS id, r.amount AS amount,
       r.ts AS ts, coalesce(r.blocked, false) AS blocked,
       coalesce(a.frozen, false) AS source_frozen, coalesce(b.frozen, false) AS target_frozen
ORDER BY id
