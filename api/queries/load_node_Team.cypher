UNWIND $rows AS row
CREATE (n:Team) SET n = row.props
RETURN count(n) AS loaded
