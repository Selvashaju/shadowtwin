
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export type Persona = "script_kiddie" | "ransomware" | "apt";

export interface TwinNode {
  id: string;
  type: "user" | "workstation" | "application" | "server" | "database" | "cloud";
  label: string;
  zone: "internet" | "corp" | "dmz" | "core" | "cloud";
  criticality: number;
  props: Record<string, unknown>;
}

export interface TwinEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  technique: string;
  difficulty: number;
  controls: string[];
}

export interface TwinControl {
  id: string;
  label: string;
  enabled: boolean;
  cost: number;
}

export interface Twin {
  org: string;
  nodes: TwinNode[];
  edges: TwinEdge[];
  controls: TwinControl[];
}

export interface AttackPath {
  entry: string;
  jewel: string;
  nodes: string[];
  edges: string[];
  hops: {
    edge: string;
    source: string;
    target: string;
    technique: string;
    technique_name: string;
    tactic: string;
    p: number;
  }[];
  likelihood: number;
}

export interface SimulateResponse {
  persona: Persona;
  controls: string[];
  entry: string[];
  breach_pct: number;
  per_jewel: Record<string, number>;
  avg_assets_compromised: number;
  paths: AttackPath[];
  blast_radius: {
    source: string[];
    assets: string[];
    count: number;
    score: number;
  };
  blocked_edges: string[];
}

export async function getTwin(): Promise<Twin> {
  const response = await fetch(`${API_BASE}/twin`);

  if (!response.ok) {
    throw new Error(`GET /twin failed: ${response.status}`);
  }

  return response.json();
}

export async function simulate(
  persona: Persona,
  controls: string[],
  entry: string[] | null = null
): Promise<SimulateResponse> {
  const response = await fetch(`${API_BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      persona,
      controls,
      entry,
      runs: 5000,
    }),
  });

  if (!response.ok) {
    throw new Error(`POST /simulate failed: ${response.status}`);
  }

  return response.json();
}
