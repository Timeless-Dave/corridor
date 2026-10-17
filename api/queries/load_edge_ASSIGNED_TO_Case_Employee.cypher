UNWIND $rows AS row
MATCH (a:Case {id: row.source})
MATCH (b:Employee {id: row.target})
CREATE (a)-[r:ASSIGNED_TO]->(b) SET r = row.props
RETURN count(r) AS loaded
