UNWIND $rows AS row
MATCH (a:Doc {id: row.source})
MATCH (b:Policy {id: row.target})
CREATE (a)-[r:DEFINES]->(b) SET r = row.props
RETURN count(r) AS loaded
