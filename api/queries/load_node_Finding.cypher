UNWIND $rows AS row
CREATE (n:Finding) SET n = row.props
RETURN count(n) AS loaded
