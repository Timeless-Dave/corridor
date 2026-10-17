MATCH (t:Team)-[:OWNS]->(c:Corridor)<-[:LEADS]-(e:Employee)
RETURN c.code, t.id, e.id ORDER BY c.code
