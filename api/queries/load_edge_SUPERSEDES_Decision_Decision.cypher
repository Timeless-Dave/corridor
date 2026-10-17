UNWIND $rows AS row
MATCH (a:Decision {id: row.source})
MATCH (b:Decision {id: row.target})
CREATE (a)-[r:SUPERSEDES]->(b) SET r = row.props
RETURN count(r) AS loaded
