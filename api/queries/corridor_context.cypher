MATCH (c:Corridor {code: $corridor_code})
OPTIONAL MATCH (lead:Employee)-[:LEADS]->(c)
OPTIONAL MATCH (t:Team)-[:OWNS]->(c)
OPTIONAL MATCH (pol:Policy)-[:APPLIES_TO]->(c)
OPTIONAL MATCH (d:Doc)-[:DEFINES]->(pol)
RETURN c.code AS corridor, lead.id AS lead_id, lead.name AS lead,
       t.id AS team_id, t.name AS team,
       collect(DISTINCT {id: pol.id, title: pol.title, rule: pol.rule,
                         threshold: pol.threshold, source_id: d.id, source: d.title}) AS policies
