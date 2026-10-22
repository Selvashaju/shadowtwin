import { useEffect, useMemo, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import type { ElementDefinition } from "cytoscape";
import { Activity, AlertTriangle, Lock, Network, RefreshCw, Shield, ShieldCheck } from "lucide-react";
import { getTwin, simulate, type Persona, type SimulateResponse, type Twin, type TwinNode, type TwinEdge, type TwinControl } from "./api";

// The Defence Planner uses the same backend URL as the other frontend API calls.
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

type DefencePlan = {
  persona: Persona;
  budget: number;
  before: number;
  after: number;
  controls: string[];
  steps: Array<{
    control: string;
    label: string;
    cost: number;
    breach_before: number;
    breach_after: number;
    drop: number;
  }>;
  blast_before: number;
  blast_after: number;
  headline: string;
};

async function requestDefencePlan(persona: Persona, entry: string, controls: string[], budget: number): Promise<DefencePlan> {
  const response = await fetch(`${API_BASE}/defend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ persona, entry: [entry], controls, budget }),
  });
  if (!response.ok) throw new Error(`Defence request failed (HTTP ${response.status})`);
  return (await response.json()) as DefencePlan;
}

const demoNodes: TwinNode[] = [
  { id: "employee", label: "HR Employee", type: "user", zone: "corp", criticality: 2, props: { entry: true } },
  { id: "workstation", label: "HR Workstation", type: "workstation", zone: "corp", criticality: 2, props: {} },
  { id: "portal", label: "HR Portal", type: "application", zone: "dmz", criticality: 3, props: {} },
  { id: "domain", label: "Domain Controller", type: "server", zone: "core", criticality: 5, props: {} },
  { id: "payroll", label: "Payroll Database", type: "database", zone: "core", criticality: 5, props: { crown_jewel: true } },
  { id: "internet", label: "Internet", type: "cloud", zone: "internet", criticality: 1, props: { entry: true } },
  { id: "chatbot", label: "AI Support Bot", type: "application", zone: "cloud", criticality: 3, props: {} },
  { id: "rag", label: "RAG Knowledge Base", type: "database", zone: "cloud", criticality: 4, props: {} },
];
const demoEdges: TwinEdge[] = [
  { id: "e1", source: "employee", target: "workstation", relation: "logs_into", technique: "T1566", difficulty: 0.3, controls: ["mfa"] },
  { id: "e2", source: "workstation", target: "portal", relation: "session", technique: "T1539", difficulty: 0.4, controls: ["edr"] },
  { id: "e3", source: "portal", target: "domain", relation: "privilege", technique: "T1078", difficulty: 0.5, controls: ["least_privilege"] },
  { id: "e4", source: "domain", target: "payroll", relation: "admin", technique: "T1021", difficulty: 0.2, controls: ["segmentation"] },
  { id: "e5", source: "internet", target: "portal", relation: "exploits", technique: "T1190", difficulty: 0.6, controls: ["waf"] },
  { id: "e6", source: "internet", target: "chatbot", relation: "prompt", technique: "AML.T0051", difficulty: 0.4, controls: ["ai_guard"] },
  { id: "e7", source: "chatbot", target: "rag", relation: "retrieves", technique: "AML.T0051", difficulty: 0.4, controls: ["ai_guard"] },
];
const demoControls: TwinControl[] = [
  { id: "mfa", label: "Multi-Factor Authentication", enabled: false, cost: 1 },
  { id: "edr", label: "Endpoint Detection & Response", enabled: false, cost: 2 },
  { id: "segmentation", label: "Network Segmentation", enabled: false, cost: 2 },
  { id: "least_privilege", label: "Least Privilege", enabled: false, cost: 2 },
  { id: "waf", label: "Web Application Firewall", enabled: false, cost: 2 },
  { id: "ai_guard", label: "AI Prompt Guardrails", enabled: false, cost: 2 },
];
const demoTwin: Twin = { org: "Acme FinServ (Sample)", nodes: demoNodes, edges: demoEdges, controls: demoControls };
const styles = [
  { selector: "node", style: { label: "data(label)", color: "#e2e8f0", "font-size": 11, "text-valign": "bottom", "text-margin-y": 8, "background-color": "#3b82f6", width: 42, height: 42, "border-width": 2, "border-color": "#93c5fd" } },
  { selector: 'node[zone="dmz"]', style: { "background-color": "#f59e0b" } },
  { selector: 'node[zone="core"]', style: { "background-color": "#8b5cf6" } },
  { selector: 'node[zone="cloud"]', style: { "background-color": "#10b981" } },
  { selector: 'node[zone="internet"]', style: { "background-color": "#f97316" } },
  { selector: "node[?jewel]", style: { width: 62, height: 62, "border-width": 5, "border-color": "#ef4444" } },
  { selector: "edge", style: { width: 2, "line-color": "#64748b", "target-arrow-color": "#64748b", "target-arrow-shape": "triangle", "curve-style": "bezier", label: "data(technique)", "font-size": 9, color: "#94a3b8" } },
  { selector: "edge.attack", style: { width: 4, "line-color": "#ef4444", "target-arrow-color": "#ef4444" } },
  { selector: "edge.blocked", style: { "line-style": "dashed", "line-color": "#475569", "target-arrow-color": "#475569", opacity: 0.35 } },
];

export default function App() {
  const [twin, setTwin] = useState<Twin>(demoTwin);
  const [live, setLive] = useState(false);
  const [apiStatus, setApiStatus] = useState("Connecting...");
  const [persona, setPersona] = useState<Persona>("apt");
  const [entry, setEntry] = useState("employee");
  const [controls, setControls] = useState<string[]>([]);
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [simStatus, setSimStatus] = useState("Waiting for real network");
  const [defencePlan, setDefencePlan] = useState<DefencePlan | null>(null);
  const [planning, setPlanning] = useState(false);
  const [planError, setPlanError] = useState("");
  const [budget, setBudget] = useState(2);

  useEffect(() => {
    let cancelled = false;
    getTwin().then(data => {
      if (cancelled) return;
      if (data.nodes.length > 0 && data.edges.length > 0) {
        setTwin(data);
        setLive(true);
        setControls(data.controls.filter(c => c.enabled).map(c => c.id));
        setEntry(data.nodes.find(n => n.props?.entry === true)?.id ?? data.nodes[0].id);
        setApiStatus("Live Network Connected");
      } else {
        setApiStatus("Demo Data — Backend Empty");
      }
    }).catch(() => { if (!cancelled) setApiStatus("Demo Data — API Unavailable"); });
    return () => { cancelled = true; };
  }, []);

  const entries = useMemo(() => twin.nodes.filter(n => n.props?.entry === true), [twin]);
  const selectedEntry = entries.some(n => n.id === entry) ? entry : entries[0]?.id;

  useEffect(() => {
    if (!live || !selectedEntry) {
      setResult(null);
      setSimStatus("Demo mode — no calculated risk");
      return;
    }
    let cancelled = false;
    setSimStatus("Simulating...");
    simulate(persona, controls, [selectedEntry]).then(data => {
      if (!cancelled) { setResult(data); setSimStatus("Simulation complete"); }
    }).catch(err => {
      if (!cancelled) { setResult(null); setSimStatus(`Simulation unavailable: ${String(err)}`); }
    });
    return () => { cancelled = true; };
  }, [live, persona, controls, selectedEntry]);

  const demoPathIds = selectedEntry === "internet" ? ["e5", "e3", "e4"] : ["e1", "e2", "e3", "e4"];
  const highlighted = live ? (result?.paths[0]?.edges ?? []) : demoPathIds;
  const blocked = useMemo(() => new Set(live && result ? result.blocked_edges : twin.edges.filter(e => e.controls.some(c => controls.includes(c))).map(e => e.id)), [live, result, twin, controls]);
  const hasStubLikeResult = live && result !== null && result.paths.length === 0 && result.breach_pct === 0 && Object.keys(result.per_jewel).length === 0 && result.blast_radius.source.length === 0;
  const elements = useMemo<ElementDefinition[]>(() => [
    ...twin.nodes.map(n => ({ data: { id: n.id, label: n.label, zone: n.zone, jewel: n.props?.crown_jewel === true } })),
    ...twin.edges.map(e => ({ data: { id: e.id, source: e.source, target: e.target, technique: e.technique }, classes: blocked.has(e.id) ? "blocked" : highlighted.includes(e.id) ? "attack" : "" })),
  ], [twin, blocked, highlighted]);

  const toggleControl = (id: string) => {
    setDefencePlan(null);
    setControls(current => current.includes(id) ? current.filter(x => x !== id) : [...current, id]);
  };
  const reset = () => {
    setDefencePlan(null);
    setPlanError("");
    setControls(twin.controls.filter(c => c.enabled).map(c => c.id));
    setPersona("apt");
    setEntry(entries[0]?.id ?? "employee");
  };
  const handlePlanDefence = async () => {
    if (!live || !selectedEntry) return;
    setPlanning(true);
    setPlanError("");
    setDefencePlan(null);
    try {
      const plan = await requestDefencePlan(persona, selectedEntry, controls, budget);
      setDefencePlan(plan);
    } catch (error) {
      setPlanError(error instanceof Error ? error.message : "Defence planning failed");
    } finally {
      setPlanning(false);
    }
  };
  const applyDefencePlan = () => {
    if (!defencePlan) return;
    const available = new Set(twin.controls.map(control => control.id));
    setControls(current => Array.from(new Set([...current, ...defencePlan.controls.filter(id => available.has(id))])));
    setDefencePlan(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 px-6 py-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3"><Shield className="text-cyan-400" size={32}/><div><h1 className="text-2xl font-bold">Shadow<span className="text-cyan-400">Twin</span></h1><p className="text-xs text-slate-400">AI-Powered Cyber Attack Simulation</p></div></div>
        <div className="flex items-center gap-2 text-sm text-emerald-400"><Activity size={16}/>{apiStatus} · {twin.nodes.length} {live ? "Live" : "Sample"} Assets</div>
      </header>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 p-5">
        <aside className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="mb-5 flex items-center gap-2 font-bold"><Lock size={18} className="text-cyan-400"/>Attack Configuration</h2>
          <label className="mb-2 block text-sm text-slate-400">Attacker Persona</label>
          <select className="mb-5 w-full rounded-lg bg-slate-800 p-3" value={persona} onChange={e => { setPersona(e.target.value as Persona); setDefencePlan(null); }}><option value="script_kiddie">Script Kiddie</option><option value="ransomware">Ransomware Gang</option><option value="apt">Advanced Persistent Threat</option></select>
          <label className="mb-2 block text-sm text-slate-400">Entry Point</label>
          <select className="mb-6 w-full rounded-lg bg-slate-800 p-3" value={selectedEntry ?? ""} onChange={e => { setEntry(e.target.value); setDefencePlan(null); }}>{entries.map(n => <option key={n.id} value={n.id}>{n.label}</option>)}</select>
          <h3 className="mb-4 font-semibold">Security Controls</h3><div className="space-y-4">{twin.controls.map(c => <label key={c.id} className="flex items-center justify-between gap-3 text-sm"><span>{c.label}</span><input type="checkbox" className="h-5 w-5 shrink-0 accent-cyan-400" checked={controls.includes(c.id)} onChange={() => toggleControl(c.id)}/></label>)}</div>
          <div className="mt-6 flex items-center justify-between gap-2 text-sm">
            <label htmlFor="budget" className="text-slate-300">Defence budget</label>
            <select id="budget" value={budget} onChange={e => { setBudget(Number(e.target.value)); setDefencePlan(null); }} className="rounded-lg bg-slate-800 px-3 py-2">
              {[1, 2, 3, 4, 5, 6].map(value => <option key={value} value={value}>{value} units</option>)}
            </select>
          </div>
          <button onClick={handlePlanDefence} disabled={!live || planning} className="mt-3 w-full rounded-lg bg-cyan-600 p-3 font-semibold hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-50"><ShieldCheck size={16} className="mr-2 inline"/>{planning ? "Planning..." : "Plan Defence"}</button>
          {planError && <p role="alert" className="mt-2 break-words text-xs text-red-400">{planError}</p>}
          <button onClick={reset} className="mt-3 w-full rounded-lg border border-slate-600 p-3 hover:bg-slate-800"><RefreshCw size={16} className="mr-2 inline"/>Reset Simulation</button>
        </aside>
        <main className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 p-5"><h2 className="flex items-center gap-2 font-bold"><Network className="text-cyan-400" size={20}/>Digital Twin Network</h2><span className="text-xs text-slate-400">{twin.nodes.length} Assets · {twin.edges.length} Relationships</span></div>
          <CytoscapeComponent elements={elements} stylesheet={styles as any} layout={{ name: "breadthfirst", directed: true, padding: 65, spacingFactor: 1.7, animate: false }} style={{ width: "100%", height: "540px" }}/>
          <div className="flex flex-wrap gap-4 border-t border-slate-800 p-4 text-xs text-slate-400"><span>🔵 Corporate</span><span>🟠 DMZ / Internet</span><span>🟣 Core</span><span>🟢 Cloud</span><span>🔴 Attack Path</span><span>⚪ Blocked Edge</span></div>
        </main>
        <aside className="space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5"><h2 className="mb-5 flex items-center gap-2 font-bold"><AlertTriangle className="text-red-400" size={19}/>Risk Overview</h2><p className="text-xs text-slate-400">Breach Probability</p><p className="mt-2 text-3xl font-extrabold text-amber-400">{live && result && !hasStubLikeResult ? `${result.breach_pct.toFixed(1)}%` : "Awaiting engine"}</p><p className="mt-2 break-words text-xs text-slate-500">{hasStubLikeResult ? "Backend returned an empty/stub-like result — no verified risk score yet." : simStatus}</p><hr className="my-5 border-slate-700"/><p className="text-sm text-slate-400">Blocked Relationships</p><p className="mt-2 text-3xl font-bold">{blocked.size} / {twin.edges.length}</p><hr className="my-5 border-slate-700"/><p className="text-sm text-slate-400">Blast Radius</p><p className="mt-2 text-3xl font-bold text-red-400">{live && result && !hasStubLikeResult ? `${result.blast_radius.count} assets` : "Awaiting engine"}</p></div>
          {defencePlan && (
            <div className="rounded-xl border border-emerald-700 bg-slate-900 p-5">
              <h2 className="mb-3 flex items-center gap-2 font-bold text-emerald-400"><ShieldCheck size={19}/>Recommended Defence</h2>
              <p className="mb-4 text-sm text-slate-300">{defencePlan.headline}</p>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg bg-slate-800 p-3"><p className="text-xs text-slate-400">Before</p><p className="text-xl font-bold text-red-400">{defencePlan.before.toFixed(1)}%</p></div>
                <div className="rounded-lg bg-slate-800 p-3"><p className="text-xs text-slate-400">After (predicted)</p><p className="text-xl font-bold text-emerald-400">{defencePlan.after.toFixed(1)}%</p></div>
              </div>
              <p className="mt-3 text-sm text-slate-300">Blast radius: {defencePlan.blast_before} → {defencePlan.blast_after} assets</p>
              <div className="mt-3 space-y-2">{defencePlan.steps.map(step => <div key={step.control} className="rounded-lg bg-slate-800 p-3 text-sm"><span className="font-semibold">{step.label}</span><p className="mt-1 text-xs text-slate-400">Cost {step.cost} · Risk reduction {step.drop.toFixed(1)} points</p></div>)}</div>
              {defencePlan.controls.length > 0 ? <button onClick={applyDefencePlan} className="mt-4 w-full rounded-lg bg-emerald-600 p-3 font-semibold hover:bg-emerald-500">Apply Recommended Controls</button> : <p className="mt-3 text-xs text-slate-400">No additional controls were recommended for this budget.</p>}
            </div>
          )}
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5"><h2 className="mb-3 flex items-center gap-2 font-bold"><ShieldCheck className="text-emerald-400" size={19}/>Defence Overview</h2><p className="mb-3 text-sm text-slate-400">Selected Security Controls</p>{controls.length === 0 ? <p className="text-sm text-amber-400">No protections enabled</p> : <div className="space-y-2">{controls.map(id => <div className="rounded-lg bg-slate-800 p-3 text-sm" key={id}>{twin.controls.find(c => c.id === id)?.label ?? id}</div>)}</div>}<p className="mt-4 text-xs text-slate-500">{live ? "Calculated simulation updates after a control changes." : "Demo controls only; real risk requires backend organization data."}</p></div>
        </aside>
      </div>
      <footer className="py-5 text-center text-xs text-slate-500">ShadowTwin · CYBERGEN 2026 · Digital Twin Security Platform</footer>
    </div>
  );
}
