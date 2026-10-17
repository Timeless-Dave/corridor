UNWIND $rows AS row
MATCH (a:Case {id: row.source})
MATCH (b:Policy {id: row.target})
CREATE (a)-[r:APPLIED]->(b) SET r = row.props
RETURN count(r) AS loaded
