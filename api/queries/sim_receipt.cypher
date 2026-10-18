MATCH (o:FreezeOrder {id: $order_id})
CREATE (m:Measurement {id: $measurement_id, before: $before, after: $after, measured_at: $now, matched_projection: $matched})
CREATE (o)-[:RECEIPT]->(m)
SET o.status = 'measured'
RETURN o.id AS order_id
