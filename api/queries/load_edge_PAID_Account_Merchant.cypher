UNWIND $rows AS row
MATCH (a:Account {id: row.source})
MATCH (b:Merchant {id: row.target})
CREATE (a)-[r:PAID]->(b) SET r = row.props
RETURN count(r) AS loaded
