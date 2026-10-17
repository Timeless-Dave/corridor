// Static 2–5 hop branches avoid closed-path projection ordering ambiguity.
MATCH (n0:Account {id: $account_id})-[r0:SENT]->(n1:Account)-[r1:SENT]->(n0)
WHERE 2 <= $max_hops
  AND n0.id <> n1.id
  AND r0.ts < r1.ts AND r0.amount > r1.amount
  AND r1.ts - r0.ts <= 259200
RETURN [n0.id, n1.id, n0.id] AS accounts,
       [r0.id, r1.id] AS transfers, [r0.amount, r1.amount] AS amounts,
       [r0.ts, r1.ts] AS timestamps, r0.amount + r1.amount AS volume
LIMIT 10
UNION ALL
MATCH (n0:Account {id: $account_id})-[r0:SENT]->(n1:Account)-[r1:SENT]->(n2:Account)-[r2:SENT]->(n0)
WHERE 3 <= $max_hops
  AND n0.id <> n1.id
  AND n0.id <> n2.id
  AND n1.id <> n2.id
  AND r0.ts < r1.ts AND r0.amount > r1.amount
  AND r1.ts < r2.ts AND r1.amount > r2.amount
  AND r2.ts - r0.ts <= 259200
RETURN [n0.id, n1.id, n2.id, n0.id] AS accounts,
       [r0.id, r1.id, r2.id] AS transfers, [r0.amount, r1.amount, r2.amount] AS amounts,
       [r0.ts, r1.ts, r2.ts] AS timestamps, r0.amount + r1.amount + r2.amount AS volume
LIMIT 10
UNION ALL
MATCH (n0:Account {id: $account_id})-[r0:SENT]->(n1:Account)-[r1:SENT]->(n2:Account)-[r2:SENT]->(n3:Account)-[r3:SENT]->(n0)
WHERE 4 <= $max_hops
  AND n0.id <> n1.id
  AND n0.id <> n2.id
  AND n0.id <> n3.id
  AND n1.id <> n2.id
  AND n1.id <> n3.id
  AND n2.id <> n3.id
  AND r0.ts < r1.ts AND r0.amount > r1.amount
  AND r1.ts < r2.ts AND r1.amount > r2.amount
  AND r2.ts < r3.ts AND r2.amount > r3.amount
  AND r3.ts - r0.ts <= 259200
RETURN [n0.id, n1.id, n2.id, n3.id, n0.id] AS accounts,
       [r0.id, r1.id, r2.id, r3.id] AS transfers, [r0.amount, r1.amount, r2.amount, r3.amount] AS amounts,
       [r0.ts, r1.ts, r2.ts, r3.ts] AS timestamps, r0.amount + r1.amount + r2.amount + r3.amount AS volume
LIMIT 10
UNION ALL
MATCH (n0:Account {id: $account_id})-[r0:SENT]->(n1:Account)-[r1:SENT]->(n2:Account)-[r2:SENT]->(n3:Account)-[r3:SENT]->(n4:Account)-[r4:SENT]->(n0)
WHERE 5 <= $max_hops
  AND n0.id <> n1.id
  AND n0.id <> n2.id
  AND n0.id <> n3.id
  AND n0.id <> n4.id
  AND n1.id <> n2.id
  AND n1.id <> n3.id
  AND n1.id <> n4.id
  AND n2.id <> n3.id
  AND n2.id <> n4.id
  AND n3.id <> n4.id
  AND r0.ts < r1.ts AND r0.amount > r1.amount
  AND r1.ts < r2.ts AND r1.amount > r2.amount
  AND r2.ts < r3.ts AND r2.amount > r3.amount
  AND r3.ts < r4.ts AND r3.amount > r4.amount
  AND r4.ts - r0.ts <= 259200
RETURN [n0.id, n1.id, n2.id, n3.id, n4.id, n0.id] AS accounts,
       [r0.id, r1.id, r2.id, r3.id, r4.id] AS transfers, [r0.amount, r1.amount, r2.amount, r3.amount, r4.amount] AS amounts,
       [r0.ts, r1.ts, r2.ts, r3.ts, r4.ts] AS timestamps, r0.amount + r1.amount + r2.amount + r3.amount + r4.amount AS volume
LIMIT 10
