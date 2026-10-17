MATCH (c:Case {id: $case_id})
OPTIONAL MATCH (c)-[:APPLIED]->(p:Policy)
OPTIONAL MATCH (doc:Doc)-[:DEFINES]->(p)
OPTIONAL MATCH (c)-[:PRECEDENT]->(d:Decision)
OPTIONAL MATCH (d)-[:MADE_BY]->(author:Employee)
OPTIONAL MATCH (c)-[:ASSIGNED_TO]->(assignee:Employee)
OPTIONAL MATCH (assignee)-[:MEMBER_OF]->(team:Team)
RETURN DISTINCT properties(p) AS policy, properties(doc) AS source,
       properties(d) AS precedent, properties(author) AS author,
       properties(assignee) AS assignee, properties(team) AS team
