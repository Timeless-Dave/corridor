CALL algo.labelPropagation({nodeLabels: ['Account', 'Device', 'Phone'],
                            relationshipTypes: ['SENT', 'USED', 'REGISTERED'], maxIterations: 10})
YIELD node, communityId
WITH node, communityId WHERE 'Account' IN labels(node)
RETURN node.id AS account, communityId AS community_id
