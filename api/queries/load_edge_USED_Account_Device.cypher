UNWIND $rows AS row
MATCH (a:Account {id: row.source})
MATCH (b:Device {fingerprint: row.target})
CREATE (a)-[r:USED]->(b) SET r = row.props
RETURN count(r) AS loaded
