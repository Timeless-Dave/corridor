UNWIND $rows AS row
CREATE (n:AjoPool) SET n = row.props
RETURN count(n) AS loaded
