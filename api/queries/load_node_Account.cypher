UNWIND $rows AS row
CREATE (n:Account) SET n = row.props
RETURN count(n) AS loaded
