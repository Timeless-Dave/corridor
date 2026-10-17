MATCH (c:Case {id: $case_id, status: 'open'})
MATCH (n) WHERE coalesce(n.id, n.fingerprint, n.number) IN $cited_ids
  AND any(label IN labels(n) WHERE label IN ['Account', 'Device', 'Phone', 'Policy', 'Decision'])
WITH c, collect(DISTINCT n) AS citations
WHERE size(citations) = size($cited_ids)
CREATE (f:Finding {id: $finding_id, step: $step, text: $text, tool: $tool,
                   query_name: $query_name, params: $params, result_json: $result_json, rejected_citations: $rejected_citations,
                   interpretation_source: $interpretation_source, created_at: $now})
CREATE (c)-[:HAS_FINDING]->(f)
WITH f, citations UNWIND citations AS n
CREATE (f)-[:CITES]->(n)
RETURN f.id AS finding_id, count(n) AS citations
