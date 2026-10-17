UNWIND $rows AS row
CREATE (n:Decision) SET n = row.props
RETURN count(n) AS loaded
