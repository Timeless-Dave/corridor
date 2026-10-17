MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY type
