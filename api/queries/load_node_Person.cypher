UNWIND $rows AS row
CREATE (n:Person) SET n = row.props
RETURN count(n) AS loaded
