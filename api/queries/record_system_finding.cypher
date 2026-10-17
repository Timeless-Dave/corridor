MATCH (c:Case {id: $case_id, status: 'open'})
CREATE (f:Finding {id: $finding_id, step: $step, text: $text, tool: 'guardrail',
                   query_name: 'guardrails.py', params: '{}', result_json: $details,
                   interpretation_source: 'deterministic', created_at: $now})
CREATE (c)-[:HAS_FINDING]->(f)
RETURN f.id AS finding_id
