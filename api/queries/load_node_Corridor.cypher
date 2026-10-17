UNWIND $rows AS row
CREATE (n:Corridor) SET n = row.props
RETURN count(n) AS loaded
