UNWIND $rows AS row
CREATE (n:Employee) SET n = row.props
RETURN count(n) AS loaded
