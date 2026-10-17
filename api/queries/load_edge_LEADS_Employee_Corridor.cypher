UNWIND $rows AS row
MATCH (a:Employee {id: row.source})
MATCH (b:Corridor {code: row.target})
CREATE (a)-[r:LEADS]->(b) SET r = row.props
RETURN count(r) AS loaded
