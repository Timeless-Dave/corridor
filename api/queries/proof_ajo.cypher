MATCH (p:AjoPool {id: $pool_id})<-[:MEMBER_OF]-(recipient:Account)
MATCH (contributor:Account)-[:MEMBER_OF]->(p)
MATCH (contributor)-[t1:SENT]->(recipient)
MATCH (contributor)-[t2:SENT]->(recipient)
WHERE t1.pool_id = p.id AND t2.pool_id = p.id
  AND t1.purpose = 'ajo_payout' AND t2.purpose = 'ajo_payout'
  AND t2.round = t1.round + 1 AND t2.ts > t1.ts
MATCH (contributor)-[:USED]->(d:Device)<-[:USED]-(recipient)
RETURN recipient.id AS recipient, t1.round AS first_round, t2.round AS next_round,
       collect(DISTINCT contributor.id) AS contributors,
       collect(DISTINCT d.fingerprint) AS devices,
       collect(DISTINCT t1.id) AS first_transfers, collect(DISTINCT t2.id) AS next_transfers
ORDER BY first_round
