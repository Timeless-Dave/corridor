UNWIND $rows AS row
CREATE (n:Policy) SET n = row.props
RETURN count(n) AS loaded
