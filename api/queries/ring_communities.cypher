CALL algo.labelPropagation({nodeLabels: ['Account', 'Device', 'Phone'],
                            relationshipTypes: ['SENT', 'USED', 'REGISTERED'], maxIterations: 10})
YIELD node, communityId
WITH node, communityId WHERE node.id IN $account_ids
RETURN communityId AS community_id, collect(node.id) AS members, count(*) AS size
ORDER BY size DESC, community_id
