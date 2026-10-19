export type Properties = Record<string, unknown>;
export type GraphNode = {
  id: string;
  labels: string[];
  properties: Properties;
};
export type GraphEdge = {
  id: number;
  source: string;
  target: string;
  type: string;
  properties: Properties;
};
export type Subgraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  possibly_truncated: boolean;
};
export type Finding = {
  id: string;
  step: number;
  tool: string;
  text: string;
  params?: string;
  result_json?: string;
  rejected_citations?: string;
  interpretation_source?: string;
};
export type Evidence = {
  finding_id: string;
  step: number;
  tool: string;
  text: string;
  cited: string[];
  query_text?: string | null;
  params: string;
};
export type CaseData = {
  case: Properties & {
    id: string;
    status: string;
    verdict?: string;
    requested_account_id?: string;
  };
  findings: Finding[];
  evidence: Evidence[];
  subgraph: Subgraph;
  routing: Properties;
  rule_check?: {
    supports: Record<string, string[]>;
    corroborated_accounts: string[];
    structural: string[];
    scratch_plan: boolean;
    freeze_allowed: boolean;
  };
  grounding: {
    policy: Properties | null;
    source: Properties | null;
    precedent: Properties | null;
    author: Properties | null;
    assignee: Properties | null;
    team: Properties | null;
  }[];
};
export type Flag = {
  account_id: string;
  country: string;
  corridor: string;
  transfers: Properties[];
  returning_account: boolean;
  open_cases: number;
};
export type HistoryCase = {
  case_id: string;
  verdict: string | null;
  pattern: string | null;
  opened_at: number;
  key_findings: string[];
};
export type StreamEvent = {
  type: string;
  case_id: string;
  tool?: string;
  text?: string;
  decision?: Properties;
  case?: Properties;
};
