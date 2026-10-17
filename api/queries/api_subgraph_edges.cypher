MATCH (a)-[r]->(b)
WHERE coalesce(a.id, a.fingerprint, a.number, a.code) IN $ids
  AND coalesce(b.id, b.fingerprint, b.number, b.code) IN $ids
RETURN DISTINCT id(r) AS id, coalesce(a.id, a.fingerprint, a.number, a.code) AS source,
       coalesce(b.id, b.fingerprint, b.number, b.code) AS target,
       type(r) AS type, properties(r) AS properties
ORDER BY id LIMIT 1000
