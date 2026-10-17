UNWIND $rows AS row
MATCH (a:Team {id: row.source})
MATCH (b:Corridor {code: row.target})
CREATE (a)-[r:OWNS]->(b) SET r = row.props
RETURN count(r) AS loaded
