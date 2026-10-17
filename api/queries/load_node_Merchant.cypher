UNWIND $rows AS row
CREATE (n:Merchant) SET n = row.props
RETURN count(n) AS loaded
