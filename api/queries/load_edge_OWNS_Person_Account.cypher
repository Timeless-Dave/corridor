UNWIND $rows AS row
MATCH (a:Person {id: row.source})
MATCH (b:Account {id: row.target})
CREATE (a)-[r:OWNS]->(b) SET r = row.props
RETURN count(r) AS loaded
