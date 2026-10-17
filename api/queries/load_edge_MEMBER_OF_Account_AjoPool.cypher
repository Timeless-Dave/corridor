UNWIND $rows AS row
MATCH (a:Account {id: row.source})
MATCH (b:AjoPool {id: row.target})
CREATE (a)-[r:MEMBER_OF]->(b) SET r = row.props
RETURN count(r) AS loaded
