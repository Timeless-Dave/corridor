UNWIND $rows AS row
MATCH (a:Finding {id: row.source})
MATCH (b:Account {id: row.target})
CREATE (a)-[r:CITES]->(b) SET r = row.props
RETURN count(r) AS loaded
