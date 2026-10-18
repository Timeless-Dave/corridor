MATCH (c:Case {id: $case_id, status: 'open'})
MATCH (pol:Policy {id: $policy_id})-[:APPLIES_TO]->(corridor:Corridor)
MATCH (employee:Employee {id: $assignee_id})-[:LEADS]->(corridor)
MATCH (decision:Decision {id: $decision_id})-[:BASED_ON]->(pol)
WHERE NOT (:Decision)-[:SUPERSEDES]->(decision)
WITH DISTINCT c, pol, employee, decision
MATCH (member:Account) WHERE member.id IN $members
WITH c, pol, employee, decision, collect(DISTINCT member) AS accounts
WHERE size(accounts) = size($members)
SET c.status = 'closed', c.verdict = $verdict, c.risk = $risk,
    c.pattern = $pattern, c.closed_at = $now, c.rationale = $rationale,
    c.proposed_verdict = $proposed_verdict, c.guardrail_reasons = $guardrail_reasons,
    c.step_cap_reached = $step_cap_reached
CREATE (c)-[:APPLIED]->(pol), (c)-[:PRECEDENT]->(decision), (c)-[:ASSIGNED_TO]->(employee)
WITH c, accounts UNWIND accounts AS member
MERGE (c)-[r:INVOLVES]->(member)
ON CREATE SET r.role = CASE WHEN member.id = c.requested_account_id THEN 'flagged' ELSE 'member' END
RETURN c.id AS case_id, c.verdict AS verdict, count(member) AS members
