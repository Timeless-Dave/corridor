CALL algo.pageRank('Account', 'SENT') YIELD node, score
WITH node, score WHERE node.id IN $account_ids
RETURN node.id AS account, score ORDER BY score DESC, account
