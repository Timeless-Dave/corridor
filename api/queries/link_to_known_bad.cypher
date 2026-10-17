MATCH (a:Account {id: $account_id}), (bad:Account)<-[:INVOLVES]-(:Case {verdict: 'FREEZE'})
WHERE a.id <> bad.id
WITH DISTINCT a, bad
CALL algo.SPpaths({sourceNode: a, targetNode: bad,
                   relTypes: ['SENT', 'USED', 'REGISTERED'], relDirection: 'both',
                   maxLen: 6, pathCount: 1})
YIELD path
RETURN a.id AS account, bad.id AS known_bad,
       [n IN nodes(path) | coalesce(n.id, n.fingerprint, n.number)] AS path,
       [r IN relationships(path) | id(r)] AS edge_ids, length(path) AS hops
ORDER BY hops, known_bad LIMIT 3
