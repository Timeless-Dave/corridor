UNWIND $rows AS row
MATCH (a:Account {id: row.source})
MATCH (b:Phone {number: row.target})
CREATE (a)-[r:REGISTERED]->(b) SET r = row.props
RETURN count(r) AS loaded
