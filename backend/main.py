import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

from fastapi.middleware.cors import CORSMiddleware
from models import (SimulateRequest, BlastRequest, DefendRequest,
                    CompareRequest, ExplainRequest, GenerateRequest)

# Engine imports (step 6a). load_twin is NOT imported here because
# main.py already has its own load_twin below.
from engine.graph import active_graph, top_paths, blast_radius
from engine.montecarlo import breach_probability
from engine.defend import plan

from ai.integration import explain_edge_ids
from models import ExplainResponse


app = FastAPI(title="ShadowTwin API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

TWIN_FILE = Path(__file__).parent / "data" / "acme_twin.json"

def load_twin():
    if TWIN_FILE.exists():
        return json.loads(TWIN_FILE.read_text())
    return {"org": "Demo", "nodes": [], "edges": [], "controls": []}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/twin")
def get_twin():
    return load_twin()

@app.post("/twin/generate")
def generate(req: GenerateRequest):
    return {"todo": "JK wires LLM here", "twin": load_twin()}

@app.post("/simulate")
def simulate(req: SimulateRequest):
    return {"persona": req.persona, "controls": req.controls or [],
            "entry": req.entry or [], "breach_pct": 0.0, "per_jewel": {},
            "avg_assets_compromised": 0.0, "paths": [],
            "blast_radius": {"source": [], "assets": [], "count": 0, "score": 0},
            "blocked_edges": []}

@app.post("/blast-radius")
def blast(req: BlastRequest):
    return {"source": [req.node], "assets": [], "count": 0, "score": 0}

@app.post("/defend")
def defend(req: DefendRequest):
    return {"persona": req.persona, "budget": req.budget, "before": 0.0,
            "after": 0.0, "steps": [], "controls": [], "ranking": [],
            "cut_edges": [], "cut_controls": [], "blast_before": 0,
            "blast_after": 0, "headline": "stub"}

@app.post("/compare")
def compare(req: CompareRequest):
    side = {"controls": [], "breach_pct": 0.0, "per_jewel": {},
            "blast_count": 0, "blast_score": 0, "path_count": 0}
    return {"persona": req.persona, "before": side, "after": side,
            "delta_breach": 0.0, "delta_blast": 0}


@app.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest):
    try:
        twin = load_twin()
        return explain_edge_ids(req.path, twin)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc
