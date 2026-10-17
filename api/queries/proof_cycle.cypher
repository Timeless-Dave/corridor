// Fixed five-account M1 proof: explicit edge aliases preserve transfer order.
MATCH (a:Account {id: $account_id})-[r0:SENT]->(b:Account)-[r1:SENT]->(c:Account)
      -[r2:SENT]->(d:Account)-[r3:SENT]->(e:Account)-[r4:SENT]->(a)
WHERE a <> b AND a <> c AND a <> d AND a <> e
  AND b <> c AND b <> d AND b <> e AND c <> d AND c <> e AND d <> e
  AND r0.ts < r1.ts AND r1.ts < r2.ts AND r2.ts < r3.ts AND r3.ts < r4.ts
  AND r0.amount > r1.amount AND r1.amount > r2.amount
  AND r2.amount > r3.amount AND r3.amount > r4.amount
  AND r4.ts - r0.ts <= 259200
RETURN [a.id, b.id, c.id, d.id, e.id, a.id] AS accounts,
       [r0.id, r1.id, r2.id, r3.id, r4.id] AS transfers,
       [r0.amount, r1.amount, r2.amount, r3.amount, r4.amount] AS amounts,
       [r0.ts, r1.ts, r2.ts, r3.ts, r4.ts] AS timestamps
