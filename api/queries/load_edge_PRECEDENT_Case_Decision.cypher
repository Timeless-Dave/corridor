UNWIND $rows AS row
MATCH (a:Case {id: row.source})
MATCH (b:Decision {id: row.target})
CREATE (a)-[r:PRECEDENT]->(b) SET r = row.props
RETURN count(r) AS loaded
