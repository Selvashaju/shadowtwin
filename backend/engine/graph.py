
import json
from pathlib import Path

import networkx as nx

SKILL = {
    "script_kiddie": 0.6,
    "ransomware": 1.0,
    "apt": 1.4,
}


def load_twin(path=None):
    if path is None:
        path = Path(__file__).resolve().parents[1] / "data" / "acme_twin.json"

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def active_graph(twin, enabled: set[str]) -> nx.DiGraph:
    G = nx.DiGraph()

    for n in twin["nodes"]:
        G.add_node(n["id"], **n)

    for e in twin["edges"]:
        if enabled.isdisjoint(e.get("controls", [])):
            G.add_edge(e["source"], e["target"], **e)

    return G


def hop_p(edge, persona):
    skill = SKILL[persona]
    difficulty = edge["difficulty"]

    return min(
        0.98,
        max(0.02, (1 - difficulty) * skill)
    )


def top_paths(G, entry, jewel, persona, k=5):
    out = []

    if entry not in G or jewel not in G:
        return out

    for p in nx.all_simple_paths(
        G, entry, jewel, cutoff=6
    ):
        prob = 1.0

        for a, b in zip(p, p[1:]):
            prob *= hop_p(G[a][b], persona)

        edges = [
            G[a][b]["id"]
            for a, b in zip(p, p[1:])
        ]

        out.append({
            "nodes": p,
            "edges": edges,
            "likelihood": round(prob, 4)
        })

    return sorted(
        out,
        key=lambda x: -x["likelihood"]
    )[:k]


def blast_radius(G, node):
    if node not in G:
        raise ValueError(f"Unknown node: {node}")

    reach = nx.descendants(G, node)

    return {
        "assets": sorted(reach),
        "score": sum(
            G.nodes[n]["criticality"]
            for n in reach
        )
    }
