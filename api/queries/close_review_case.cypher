MATCH (c:Case {id: $case_id, status: 'open'})
SET c.status = 'closed', c.verdict = 'MONITOR', c.risk = $risk, c.pattern = 'none',
    c.closed_at = $now, c.error = 'review_required', c.rationale = $reason,
    c.step_cap_reached = $step_cap_reached
RETURN c.id AS case_id, c.verdict AS verdict
