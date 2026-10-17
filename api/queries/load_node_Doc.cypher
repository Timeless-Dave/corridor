UNWIND $rows AS row
CREATE (n:Doc) SET n = row.props
RETURN count(n) AS loaded
