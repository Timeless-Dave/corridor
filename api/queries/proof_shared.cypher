MATCH (a:Account {id: $account_id})-[:USED|REGISTERED]->(identifier)<-[:USED|REGISTERED]-(member:Account)
WITH collect(DISTINCT member) AS members
UNWIND members AS m
MATCH (owner:Person)-[:OWNS]->(m)
MATCH (m)-[:USED]->(device:Device)
MATCH (m)-[:REGISTERED]->(phone:Phone)
RETURN collect(DISTINCT m.id) AS accounts, collect(DISTINCT owner.id) AS owners,
       collect(DISTINCT device.fingerprint) AS devices, collect(DISTINCT phone.number) AS phones
