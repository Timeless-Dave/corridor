UNWIND $rows AS row
MATCH (a:Decision {id: row.source})
MATCH (b:Policy {id: row.target})
CREATE (a)-[r:BASED_ON]->(b) SET r = row.props
RETURN count(r) AS loaded
