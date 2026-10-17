UNWIND $rows AS row
CREATE (n:Phone) SET n = row.props
RETURN count(n) AS loaded
