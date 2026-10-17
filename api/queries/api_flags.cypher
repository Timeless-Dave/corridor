MATCH (a:Account {flagged: true})
OPTIONAL MATCH (a)-[tx:SENT]-(:Account)
WITH a, tx ORDER BY tx.ts DESC, tx.id
WITH a, collect(DISTINCT properties(tx))[..1] AS transfers
OPTIONAL MATCH (a)<-[:INVOLVES]-(c:Case)
RETURN a.id AS account_id, a.country AS country, transfers,
       count(DISTINCT c) > 0 AS returning_account,
       count(DISTINCT CASE WHEN c.status = 'open' THEN c ELSE null END) AS open_cases
ORDER BY account_id
