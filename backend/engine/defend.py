
import networkx as nx

from .graph import active_graph
from .montecarlo import breach_probability


def min_cut_edges(G, entries, jewels):
    H = G.copy()

    source = "__SHADOWTWIN_SRC__"
    sink = "__SHADOWTWIN_SNK__"

    H.add_edges_from(
        (source, e)
        for e in entries
    )

    H.add_edges_from(
        (j, sink)
        for j in jewels
    )

    cut = nx.minimum_edge_cut(
        H,
        source,
        sink
    )

    return [
        {
            "source": u,
            "target": v,
            "id": G[u][v]["id"]
        }
        for u, v in cut
        if u in G
        and v in G
        and G.has_edge(u, v)
    ]


def plan(
    twin,
    entries,
    jewels,
    persona,
    budget=2
):
    chosen = set()

    base = breach_probability(
        active_graph(twin, chosen),
        entries,
        jewels,
        persona
    )

    steps = []

    for _ in range(budget):
        best = None
        best_p = None

        for c in twin["controls"]:
            control_id = c["id"]

            if control_id in chosen:
                continue

            graph = active_graph(
                twin,
                chosen | {control_id}
            )

            p = breach_probability(
                graph,
                entries,
                jewels,
                persona
            )

            if best_p is None or p < best_p:
                best = control_id
                best_p = p

        if best is None:
            break

        chosen.add(best)

        steps.append({
            "control": best,
            "breach_after": best_p
        })

    return {
        "before": base,
        "steps": steps,
        "controls": sorted(chosen)
    }
