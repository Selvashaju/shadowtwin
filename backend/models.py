"""Frozen API contract for ShadowTwin. Everyone codes against these models.

Change nothing here after 0:30 without telling the whole team.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

NodeType = Literal["user", "workstation", "application", "server", "database", "cloud"]
Zone = Literal["internet", "corp", "dmz", "core", "cloud"]
Persona = Literal["script_kiddie", "ransomware", "apt"]


# ---------------------------------------------------------------- twin schema
class Node(BaseModel):
    id: str
    type: NodeType
    label: str
    zone: Zone
    criticality: int = Field(ge=1, le=5)
    props: dict = Field(default_factory=dict)  # entry: bool, crown_jewel: bool, mfa, edr, ...


class Edge(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    technique: str  # MITRE ATT&CK (T1566) or ATLAS (AML.T0051) ID
    difficulty: float = Field(ge=0, le=1)  # lower = easier for attacker
    controls: list[str] = Field(default_factory=list)  # control IDs that block this edge


class Control(BaseModel):
    id: str
    label: str
    enabled: bool = False
    cost: int = Field(default=1, ge=1, le=5)  # relative effort / budget units


class Twin(BaseModel):
    org: str
    nodes: list[Node]
    edges: list[Edge]
    controls: list[Control]

    @model_validator(mode="after")
    def _consistent(self) -> "Twin":
        node_ids = [n.id for n in self.nodes]
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("duplicate node id")
        edge_ids = [e.id for e in self.edges]
        if len(set(edge_ids)) != len(edge_ids):
            raise ValueError("duplicate edge id")
        ctrl_ids = {c.id for c in self.controls}
        nodes = set(node_ids)
        for e in self.edges:
            if e.source not in nodes or e.target not in nodes:
                raise ValueError(f"edge {e.id} points to unknown node")
            unknown = set(e.controls) - ctrl_ids
            if unknown:
                raise ValueError(f"edge {e.id} uses unknown controls {sorted(unknown)}")
        if not any(n.props.get("entry") for n in self.nodes):
            raise ValueError("twin needs at least one node with props.entry = true")
        if not any(n.props.get("crown_jewel") for n in self.nodes):
            raise ValueError("twin needs at least one node with props.crown_jewel = true")
        return self


# ---------------------------------------------------------------- shared parts
class Hop(BaseModel):
    edge: str
    source: str
    target: str
    technique: str
    technique_name: str
    tactic: str
    p: float  # hop success probability for the persona


class AttackPath(BaseModel):
    entry: str
    jewel: str
    nodes: list[str]
    edges: list[str]
    hops: list[Hop]
    likelihood: float


class BlastRadius(BaseModel):
    source: list[str]
    assets: list[str]
    count: int
    score: int


# ---------------------------------------------------------------- requests
class SimulateRequest(BaseModel):
    entry: list[str] | None = None  # default: all entry nodes
    persona: Persona = "apt"
    controls: list[str] | None = None  # enabled control IDs; default: twin's enabled flags
    runs: int = Field(default=5000, ge=100, le=50000)


class BlastRequest(BaseModel):
    node: str
    controls: list[str] | None = None


class DefendRequest(BaseModel):
    budget: int = Field(default=2, ge=1, le=6)
    persona: Persona = "apt"
    entry: list[str] | None = None
    controls: list[str] = Field(default_factory=list)  # already-enabled baseline


class CompareRequest(BaseModel):
    before: list[str] = Field(default_factory=list)
    after: list[str] = Field(default_factory=list)
    persona: Persona = "apt"
    entry: list[str] | None = None


class ExplainRequest(BaseModel):
    path: list[str]  # edge IDs in order
    persona: Persona = "apt"


class GenerateRequest(BaseModel):
    description: str = Field(min_length=10)


class StixRequest(BaseModel):
    persona: Persona = "apt"
    controls: list[str] | None = None
    entry: list[str] | None = None


# ---------------------------------------------------------------- responses
class SimulateResponse(BaseModel):
    persona: Persona
    controls: list[str]
    entry: list[str]
    breach_pct: float
    per_jewel: dict[str, float]
    avg_assets_compromised: float
    paths: list[AttackPath]
    blast_radius: BlastRadius
    blocked_edges: list[str]


class DefendStep(BaseModel):
    control: str
    label: str
    cost: int
    breach_before: float
    breach_after: float
    drop: float


class ControlEffect(BaseModel):
    control: str
    label: str
    cost: int
    breach_after: float
    drop: float


class DefendResponse(BaseModel):
    persona: Persona
    budget: int
    before: float
    after: float
    steps: list[DefendStep]
    controls: list[str]
    ranking: list[ControlEffect]  # every single control's effect from the baseline
    cut_edges: list[str]  # min-cut chokepoint edges
    cut_controls: list[str]  # controls that can block those edges
    blast_before: int
    blast_after: int
    headline: str


class CompareSide(BaseModel):
    controls: list[str]
    breach_pct: float
    per_jewel: dict[str, float]
    blast_count: int
    blast_score: int
    path_count: int


class CompareResponse(BaseModel):
    persona: Persona
    before: CompareSide
    after: CompareSide
    delta_breach: float
    delta_blast: int


class ExplainStep(BaseModel):
    edge: str
    technique: str
    text: str


class ExplainResponse(BaseModel):
    steps: list[ExplainStep]
    summary: str
    source: Literal["template", "llm"]
