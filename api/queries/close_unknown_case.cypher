MATCH (c:Case {id: $case_id, status: 'open'})
OPTIONAL MATCH (a:Account {id: c.requested_account_id})
WITH c, a WHERE a IS NULL
SET c.status = 'closed', c.verdict = 'CLEAR', c.risk = 0.0, c.pattern = 'none',
    c.closed_at = $now, c.error = 'unknown_account', c.rationale = 'Account does not exist; no investigation performed.'
RETURN c.id AS case_id, c.verdict AS verdict
