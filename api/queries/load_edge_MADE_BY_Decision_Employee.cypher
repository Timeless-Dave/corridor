UNWIND $rows AS row
MATCH (a:Decision {id: row.source})
MATCH (b:Employee {id: row.target})
CREATE (a)-[r:MADE_BY]->(b) SET r = row.props
RETURN count(r) AS loaded
