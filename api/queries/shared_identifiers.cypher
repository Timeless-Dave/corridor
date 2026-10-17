MATCH (a:Account {id: $account_id})-[ra:USED|REGISTERED]->(x)<-[rb:USED|REGISTERED]-(b:Account)
WHERE b.id <> a.id
RETURN DISTINCT b.id AS account, labels(x)[0] AS via,
       coalesce(x.fingerprint, x.number) AS identifier, id(ra) AS source_edge, id(rb) AS peer_edge
ORDER BY account, identifier
