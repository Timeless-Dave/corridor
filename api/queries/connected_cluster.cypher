CALL algo.WCC({nodeLabels: ['Account', 'Device', 'Phone'], relationshipTypes: ['USED', 'REGISTERED']})
YIELD node, componentId
WITH componentId, collect(node) AS members
WHERE any(m IN members WHERE m.id = $account_id)
RETURN componentId AS component_id,
       [m IN members | coalesce(m.id, m.fingerprint, m.number)] AS members,
       size(members) AS size
