MATCH (a:FlowNode)-[f:FLOW]->(b:FlowNode)
RETURN a.id AS source, a.side AS source_side, b.id AS target, b.side AS target_side, f.cap AS cap
