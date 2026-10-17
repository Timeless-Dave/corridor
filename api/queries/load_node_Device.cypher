UNWIND $rows AS row
CREATE (n:Device) SET n = row.props
RETURN count(n) AS loaded
