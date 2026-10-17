UNWIND $rows AS row
MATCH (a:Case {id: row.source})
MATCH (b:Account {id: row.target})
CREATE (a)-[r:INVOLVES]->(b) SET r = row.props
RETURN count(r) AS loaded
