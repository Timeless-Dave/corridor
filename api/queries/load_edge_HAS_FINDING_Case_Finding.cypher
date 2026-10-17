UNWIND $rows AS row
MATCH (a:Case {id: row.source})
MATCH (b:Finding {id: row.target})
CREATE (a)-[r:HAS_FINDING]->(b) SET r = row.props
RETURN count(r) AS loaded
