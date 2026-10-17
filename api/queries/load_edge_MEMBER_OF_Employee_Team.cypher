UNWIND $rows AS row
MATCH (a:Employee {id: row.source})
MATCH (b:Team {id: row.target})
CREATE (a)-[r:MEMBER_OF]->(b) SET r = row.props
RETURN count(r) AS loaded
