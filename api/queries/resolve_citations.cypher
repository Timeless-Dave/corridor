MATCH (n) WHERE coalesce(n.id, n.fingerprint, n.number) IN $ids
  AND any(label IN labels(n) WHERE label IN ['Account','Device','Phone','Policy','Decision','Employee','Team','Doc'])
RETURN coalesce(n.id, n.fingerprint, n.number) AS id, labels(n) AS labels
