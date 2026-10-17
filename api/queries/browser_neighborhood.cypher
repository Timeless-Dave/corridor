MATCH p = (a:Account {id: $account_id})-[*1..2]-(n)
RETURN p LIMIT 100
