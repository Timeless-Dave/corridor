MATCH (a:Account)-[r:SENT]->(b:Account)
WHERE a.id IN $freeze_ids OR b.id IN $freeze_ids
DELETE r
