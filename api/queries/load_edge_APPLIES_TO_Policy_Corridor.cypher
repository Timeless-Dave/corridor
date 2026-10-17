UNWIND $rows AS row
MATCH (a:Policy {id: row.source})
MATCH (b:Corridor {code: row.target})
CREATE (a)-[r:APPLIES_TO]->(b) SET r = row.props
RETURN count(r) AS loaded
