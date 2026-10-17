MATCH (c:Case {id: $case_id, status: 'open'})
CREATE (f:Finding {id: $finding_id, step: $step, text: $text, tool: $tool,
                   query_name: $query_name, params: $params, result_json: $result_json, rejected_citations: $rejected_citations,
                   interpretation_source: $interpretation_source, created_at: $now})
CREATE (c)-[:HAS_FINDING]->(f)
RETURN f.id AS finding_id, 0 AS citations
