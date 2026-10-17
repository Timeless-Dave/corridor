MATCH (p:AjoPool {id: $pool_id})<-[membership:MEMBER_OF]-(member:Account)
OPTIONAL MATCH (member)-[payout:SENT]->(recipient:Account)
WHERE payout.pool_id = $pool_id AND payout.purpose = 'ajo_payout'
RETURN p, membership, member, payout, recipient
