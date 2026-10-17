UNWIND $rows AS row
MATCH (a:Account {id: row.source})
MATCH (b:Account {id: row.target})
CREATE (a)-[r:SENT]->(b) SET r = row.props
RETURN count(r) AS loaded
