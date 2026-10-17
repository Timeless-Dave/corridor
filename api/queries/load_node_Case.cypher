UNWIND $rows AS row
CREATE (n:Case) SET n = row.props
RETURN count(n) AS loaded
