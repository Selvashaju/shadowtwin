
import json
import itertools
from pathlib import Path

import networkx as nx
import numpy as np

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import (
    Twin,
    SimulateRequest,
    SimulateResponse,
    BlastRequest,
    BlastRadius,
    DefendRequest,
    DefendResponse,
    CompareRequest,
    CompareResponse,
    ExplainRequest,
    ExplainResponse,
    GenerateRequest,
)

from engine.graph import (
    active_graph,
    top_paths,
    blast_radius,
    hop_p,
)
from engine.montecarlo import breach_probability

# JK's existing MITRE explanation integration
from ai.integration import explain_edge_ids


# =====================================================
# FASTAPI APPLICATION
# =====================================================

app = FastAPI(
    title="ShadowTwin API",
    version="1.1.0",
    description="Cyber Attack Graph, Simulation and Defence Engine",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TWIN_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "acme_twin.json"
)


# =====================================================
# DIGITAL TWIN HELPERS
# =====================================================

def load_twin():
    if not TWIN_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail="acme_twin.json missing",
        )

    try:
        data = json.loads(
            TWIN_FILE.read_text(encoding="utf-8")
        )
        Twin.model_validate(data)
        return data

    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid digital twin: {exc}",
        )


def get_entries(twin):
    return [
        n["id"]
        for n in twin["nodes"]
        if n.get("props", {}).get("entry")
    ]


def get_jewels(twin):
    return [
        n["id"]
        for n in twin["nodes"]
        if n.get("props", {}).get("crown_jewel")
    ]


def resolve_entries(twin, requested=None):
    entries = (
        get_entries(twin)
        if requested is None
        else list(dict.fromkeys(requested))
    )

    valid = {n["id"] for n in twin["nodes"]}

    if not set(entries).issubset(valid):
        raise HTTPException(
            status_code=422,
            detail="Unknown entry node",
        )

    return entries


def resolve_controls(twin, requested=None):
    if requested is None:
        enabled = {
            c["id"]
            for c in twin["controls"]
            if c.get("enabled", False)
        }
    else:
        enabled = set(requested)

    valid = {c["id"] for c in twin["controls"]}

    if not enabled.issubset(valid):
        raise HTTPException(
            status_code=422,
            detail="Unknown control ID",
        )

    return enabled


# =====================================================
# GRAPH ANALYSIS
# =====================================================

def graph_blast(G, entries):
    reachable = set()

    for entry in entries:
        if entry in G:
            reachable.update(
                nx.descendants(G, entry)
            )

    reachable.difference_update(entries)

    return {
        "source": entries,
        "assets": sorted(reachable),
        "count": len(reachable),
        "score": sum(
            G.nodes[n].get("criticality", 1)
            for n in reachable
        ),
    }


def graph_paths(G, entries, jewels, persona):
    paths = []

    for entry in entries:
        for jewel in jewels:
            if entry not in G or jewel not in G:
                continue

            candidates = top_paths(
                G, entry, jewel, persona, k=5
            )

            for item in candidates:
                hops = []

                for u, v in zip(
                    item["nodes"],
                    item["nodes"][1:],
                ):
                    edge = G[u][v]

                    hops.append({
                        "edge": edge["id"],
                        "source": u,
                        "target": v,
                        "technique": edge["technique"],
                        "technique_name": edge.get(
                            "relation", "Unknown"
                        ),
                        "tactic": "unknown",
                        "p": round(
                            hop_p(edge, persona), 4
                        ),
                    })

                paths.append({
                    "entry": entry,
                    "jewel": jewel,
                    "nodes": item["nodes"],
                    "edges": item["edges"],
                    "hops": hops,
                    "likelihood": item["likelihood"],
                })

    return sorted(
        paths,
        key=lambda p: -p["likelihood"],
    )[:5]


def graph_cut_edges(G, entries, jewels):
    source = "__shadowtwin_source__"
    sink = "__shadowtwin_sink__"

    H = nx.DiGraph()

    for u, v in G.edges():
        H.add_edge(u, v, capacity=1)

    high = G.number_of_edges() + 1

    for entry in entries:
        if entry in G:
            H.add_edge(
                source, entry, capacity=high
            )

    for jewel in jewels:
        if jewel in G:
            H.add_edge(
                jewel, sink, capacity=high
            )

    if source not in H or sink not in H:
        return []

    _, partition = nx.minimum_cut(
        H, source, sink, capacity="capacity"
    )

    reachable, non_reachable = partition
    ids = []

    for u in reachable:
        for v in H.successors(u):
            if (
                v in non_reachable
                and G.has_edge(u, v)
            ):
                ids.append(G[u][v]["id"])

    return sorted(set(ids))


# =====================================================
# SIMULATION HELPERS
# =====================================================

def simulate_probability(
    G, entries, jewels, persona, runs=5000
):
    if not entries or not jewels:
        return 0.0

    return breach_probability(
        G,
        entries,
        jewels,
        persona,
        runs=runs,
        seed=42,
    )


def average_compromised(
    G, entries, persona, runs=5000
):
    if not entries:
        return 0.0

    rng = np.random.default_rng(42)
    total = 0

    for _ in range(runs):
        start = entries[
            rng.integers(len(entries))
        ]

        seen = {start}
        frontier = [start]

        while frontier:
            next_frontier = []

            for u in frontier:
                for v in G.successors(u):
                    if v not in seen:
                        if rng.random() < hop_p(
                            G[u][v], persona
                        ):
                            seen.add(v)
                            next_frontier.append(v)

            frontier = next_frontier

        total += len(seen) - 1

    return round(total / runs, 2)


def evaluate(
    twin,
    entries,
    jewels,
    persona,
    controls,
    runs=5000,
):
    G = active_graph(twin, set(controls))

    breach = simulate_probability(
        G, entries, jewels, persona, runs
    )

    per_jewel = {
        jewel: simulate_probability(
            G, entries, [jewel], persona, runs
        )
        for jewel in jewels
    }

    blast = graph_blast(G, entries)
    paths = graph_paths(
        G, entries, jewels, persona
    )

    return {
        "graph": G,
        "breach": breach,
        "per_jewel": per_jewel,
        "blast": blast,
        "paths": paths,
    }


# =====================================================
# HEALTH
# =====================================================

@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "ShadowTwin",
        "engine": "online",
    }


# =====================================================
# DIGITAL TWIN
# =====================================================

@app.get("/twin", response_model=Twin)
def get_twin():
    return load_twin()


# =====================================================
# AI DIGITAL TWIN GENERATION
# =====================================================

@app.post("/twin/generate")
def generate(req: GenerateRequest):
    raise HTTPException(
        status_code=501,
        detail="AI twin generation not yet integrated",
    )


# =====================================================
# ATTACK SIMULATION
# =====================================================

@app.post(
    "/simulate",
    response_model=SimulateResponse,
)
def simulate(req: SimulateRequest):
    twin = load_twin()

    entries = resolve_entries(
        twin, req.entry
    )
    jewels = get_jewels(twin)

    controls = resolve_controls(
        twin, req.controls
    )

    result = evaluate(
        twin,
        entries,
        jewels,
        req.persona,
        controls,
        req.runs,
    )

    blocked = [
        edge["id"]
        for edge in twin["edges"]
        if not controls.isdisjoint(
            edge.get("controls", [])
        )
    ]

    return {
        "persona": req.persona,
        "controls": sorted(controls),
        "entry": entries,
        "breach_pct": result["breach"],
        "per_jewel": result["per_jewel"],
        "avg_assets_compromised": (
            average_compromised(
                result["graph"],
                entries,
                req.persona,
                req.runs,
            )
        ),
        "paths": result["paths"],
        "blast_radius": result["blast"],
        "blocked_edges": blocked,
    }


# =====================================================
# BLAST RADIUS
# =====================================================

@app.post(
    "/blast-radius",
    response_model=BlastRadius,
)
def blast(req: BlastRequest):
    twin = load_twin()

    controls = resolve_controls(
        twin, req.controls
    )

    G = active_graph(twin, controls)

    if req.node not in G:
        raise HTTPException(
            status_code=404,
            detail="Node not found",
        )

    result = blast_radius(G, req.node)

    return {
        "source": [req.node],
        "assets": result["assets"],
        "count": len(result["assets"]),
        "score": result["score"],
    }


# =====================================================
# AUTOMATIC DEFENCE PLANNER
# =====================================================

@app.post(
    "/defend",
    response_model=DefendResponse,
)
def defend(req: DefendRequest):
    twin = load_twin()

    entries = resolve_entries(
        twin, req.entry
    )
    jewels = get_jewels(twin)

    baseline = resolve_controls(
        twin, req.controls
    )

    control_map = {
        c["id"]: c
        for c in twin["controls"]
    }

    candidates = [
        c for c in twin["controls"]
        if c["id"] not in baseline
    ]

    cache = {}

    def risk(controls):
        key = frozenset(controls)

        if key not in cache:
            G = active_graph(twin, set(key))
            cache[key] = simulate_probability(
                G, entries, jewels,
                req.persona, 5000
            )

        return cache[key]

    before = risk(baseline)

    ranking = []

    for c in candidates:
        after = risk(
            baseline | {c["id"]}
        )

        ranking.append({
            "control": c["id"],
            "label": c["label"],
            "cost": c["cost"],
            "breach_after": after,
            "drop": round(before - after, 1),
        })

    ranking.sort(
        key=lambda x: (
            -x["drop"],
            x["cost"],
            x["control"],
        )
    )

    best_controls = set()
    best_risk = before
    best_cost = 0

    affordable = [
        c for c in candidates
        if c["cost"] <= req.budget
    ]

    for size in range(
        1, len(affordable) + 1
    ):
        for combo in itertools.combinations(
            affordable, size
        ):
            total_cost = sum(
                c["cost"] for c in combo
            )

            if total_cost > req.budget:
                continue

            selected = {
                c["id"] for c in combo
            }

            after = risk(
                baseline | selected
            )

            if (
                after < best_risk
                or (
                    after == best_risk
                    and total_cost < best_cost
                )
            ):
                best_risk = after
                best_controls = selected
                best_cost = total_cost

    steps = []
    active = set(baseline)
    remaining = set(best_controls)
    current_risk = before

    while remaining:
        next_id = min(
            remaining,
            key=lambda cid: (
                risk(active | {cid}),
                control_map[cid]["cost"],
                cid,
            )
        )

        next_risk = risk(
            active | {next_id}
        )
        c = control_map[next_id]

        steps.append({
            "control": next_id,
            "label": c["label"],
            "cost": c["cost"],
            "breach_before": current_risk,
            "breach_after": next_risk,
            "drop": round(
                current_risk - next_risk, 1
            ),
        })

        active.add(next_id)
        remaining.remove(next_id)
        current_risk = next_risk

    before_graph = active_graph(
        twin, baseline
    )
    after_graph = active_graph(
        twin, active
    )

    before_blast = graph_blast(
        before_graph, entries
    )
    after_blast = graph_blast(
        after_graph, entries
    )

    cut_edges = graph_cut_edges(
        before_graph, entries, jewels
    )

    cut_controls = sorted({
        cid
        for edge in twin["edges"]
        if edge["id"] in cut_edges
        for cid in edge.get("controls", [])
    })

    reduction = round(
        before - current_risk, 1
    )

    if best_controls:
        headline = (
            f"Reduce simulated breach risk "
            f"by {reduction} percentage points "
            f"with cost {best_cost}"
        )
    else:
        headline = (
            "No risk-reducing control set "
            "found within the budget"
        )

    return {
        "persona": req.persona,
        "budget": req.budget,
        "before": before,
        "after": current_risk,
        "steps": steps,
        "controls": sorted(active),
        "ranking": ranking,
        "cut_edges": cut_edges,
        "cut_controls": cut_controls,
        "blast_before": before_blast["count"],
        "blast_after": after_blast["count"],
        "headline": headline,
    }


# =====================================================
# BEFORE / AFTER COMPARISON
# =====================================================

@app.post(
    "/compare",
    response_model=CompareResponse,
)
def compare(req: CompareRequest):
    twin = load_twin()
    entries = resolve_entries(twin)
    jewels = get_jewels(twin)

    before_controls = resolve_controls(
        twin, req.before
    )
    after_controls = resolve_controls(
        twin, req.after
    )

    before = evaluate(
        twin,
        entries,
        jewels,
        req.persona,
        before_controls,
    )

    after = evaluate(
        twin,
        entries,
        jewels,
        req.persona,
        after_controls,
    )

    def side(result, controls):
        return {
            "controls": sorted(controls),
            "breach_pct": result["breach"],
            "per_jewel": result["per_jewel"],
            "blast_count": (
                result["blast"]["count"]
            ),
            "blast_score": (
                result["blast"]["score"]
            ),
            "path_count": (
                len(result["paths"])
            ),
        }

    return {
        "persona": req.persona,
        "before": side(
            before, before_controls
        ),
        "after": side(
            after, after_controls
        ),
        "delta_breach": round(
            after["breach"] - before["breach"],
            1,
        ),
        "delta_blast": (
            after["blast"]["count"]
            - before["blast"]["count"]
        ),
    }


# =====================================================
# JK OFFLINE MITRE EXPLANATION
# =====================================================

@app.post(
    "/explain",
    response_model=ExplainResponse,
)
def explain(req: ExplainRequest):
    twin = load_twin()

    try:
        return explain_edge_ids(
            req.path,
            twin
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc)
        )
