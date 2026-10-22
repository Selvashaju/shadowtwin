import json
from pathlib import Path

import networkx as nx


DATA_FILE = (
    Path(__file__).parent
    / "data"
    / "acme_twin.json"
)


MITRE_TECHNIQUES = {
    "T1566": {
        "name": "Phishing",
        "tactic": "Initial Access",
        "description": "A user or system may be exposed through a malicious communication or entry point."
    },
    "T1539": {
        "name": "Steal Web Session Cookie",
        "tactic": "Credential Access",
        "description": "A stolen web session can allow an attacker to reuse an authenticated session."
    },
    "T1078": {
        "name": "Valid Accounts",
        "tactic": "Defense Evasion / Persistence",
        "description": "Compromised legitimate credentials may be used to access trusted systems."
    },
    "T1021": {
        "name": "Remote Services",
        "tactic": "Lateral Movement",
        "description": "Remote services can provide a path from one compromised system to another."
    },
}


def load_twin() -> dict:
    """Load the Acme FinServ digital-twin dataset."""

    with DATA_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def build_graph(twin: dict) -> nx.DiGraph:
    """Convert the twin JSON into a directed graph."""

    graph = nx.DiGraph()

    for node in twin["nodes"]:
        graph.add_node(
            node["id"],
            **node
        )

    for edge in twin["edges"]:
        graph.add_edge(
            edge["source"],
            edge["target"],
            **edge
        )

    return graph


def get_mitre_info(technique: str | None) -> dict:
    """Return readable MITRE ATT&CK information."""

    if not technique:
        return {
            "id": "Unknown",
            "name": "Unmapped Technique",
            "tactic": "Unknown",
            "description": "No technique mapping is available."
        }

    technique = str(technique)

    info = MITRE_TECHNIQUES.get(
        technique
    )

    if info:
        return {
            "id": technique,
            **info
        }

    return {
        "id": technique,
        "name": "Mapped Technique",
        "tactic": "Unknown",
        "description": "A technique identifier is associated with this relationship."
    }


def calculate_risk(
    path_count: int,
    target_criticality: int,
    average_difficulty: float,
    unique_techniques: int
) -> dict:
    """
    Calculate a simple explainable risk score.

    This is intentionally deterministic so judges can understand
    how the result was produced.
    """

    score = 0

    # More reachable paths increase exposure.
    score += min(path_count * 15, 45)

    # Critical assets increase impact.
    score += min(target_criticality * 10, 40)

    # Easier attack paths increase likelihood.
    score += max(
        0,
        int((1.0 - average_difficulty) * 15)
    )

    # Multiple techniques indicate a broader attack chain.
    score += min(unique_techniques * 3, 15)

    score = min(score, 100)

    if score >= 70:
        level = "HIGH"
    elif score >= 40:
        level = "MODERATE"
    else:
        level = "LOW"

    return {
        "score": score,
        "level": level
    }


def find_attack_paths(
    source: str,
    target: str
) -> list[dict]:
    """Find available attack paths between two assets."""

    twin = load_twin()
    graph = build_graph(twin)

    if source not in graph:
        raise ValueError(
            f"Unknown source node: {source}"
        )

    if target not in graph:
        raise ValueError(
            f"Unknown target node: {target}"
        )

    paths = []

    try:
        all_paths = nx.all_simple_paths(
            graph,
            source=source,
            target=target,
            cutoff=8
        )

        for path in all_paths:

            path_edges = []

            for left, right in zip(
                path,
                path[1:]
            ):

                edge = graph[left][right]

                technique = edge.get(
                    "technique"
                )

                mitre = get_mitre_info(
                    technique
                )

                path_edges.append({
                    "source": left,
                    "target": right,
                    "relation": edge.get(
                        "relation"
                    ),
                    "technique": technique,
                    "technique_name": mitre["name"],
                    "tactic": mitre["tactic"],
                    "difficulty": edge.get(
                        "difficulty"
                    ),
                    "controls": edge.get(
                        "controls",
                        []
                    )
                })

            techniques = list(
                dict.fromkeys(
                    edge["technique"]
                    for edge in path_edges
                    if edge.get("technique")
                )
            )

            controls = list(
                dict.fromkeys(
                    control
                    for edge in path_edges
                    for control in edge.get(
                        "controls",
                        []
                    )
                )
            )

            paths.append({
                "nodes": path,
                "edges": path_edges,
                "hops": len(path) - 1,
                "techniques": techniques,
                "controls": controls
            })

    except nx.NetworkXNoPath:
        return []

    return sorted(
        paths,
        key=lambda item: (
            item["hops"],
            len(item["techniques"])
        )
    )


def analyze_attack(
    source: str,
    target: str
) -> dict:
    """
    Run an explainable attack analysis.

    Returns paths, risk, MITRE mappings and
    recommended controls.
    """

    twin = load_twin()

    graph = build_graph(twin)

    if source not in graph:
        raise ValueError(
            f"Unknown source node: {source}"
        )

    if target not in graph:
        raise ValueError(
            f"Unknown target node: {target}"
        )

    paths = find_attack_paths(
        source,
        target
    )

    target_data = graph.nodes[target]

    target_criticality = int(
        target_data.get(
            "criticality",
            1
        )
    )

    all_techniques = []

    all_controls = []

    difficulties = []

    for path in paths:

        all_techniques.extend(
            path.get(
                "techniques",
                []
            )
        )

        all_controls.extend(
            path.get(
                "controls",
                []
            )
        )

        for edge in path.get(
            "edges",
            []
        ):
            difficulty = edge.get(
                "difficulty"
            )

            if isinstance(
                difficulty,
                (int, float)
            ):
                difficulties.append(
                    float(difficulty)
                )

    unique_techniques = list(
        dict.fromkeys(
            all_techniques
        )
    )

    unique_controls = list(
        dict.fromkeys(
            all_controls
        )
    )

    average_difficulty = (
        sum(difficulties)
        / len(difficulties)
        if difficulties
        else 1.0
    )

    risk = calculate_risk(
        path_count=len(paths),
        target_criticality=target_criticality,
        average_difficulty=average_difficulty,
        unique_techniques=len(
            unique_techniques
        )
    )

    mitre = [
        get_mitre_info(
            technique
        )
        for technique in unique_techniques
    ]

    defence_map = {
        "mfa": {
            "label": "Multi-Factor Authentication",
            "reason": "Reduce the chance of stolen credentials being sufficient for access."
        },
        "email_filter": {
            "label": "Email Filtering",
            "reason": "Reduce malicious communication and phishing-based entry points."
        },
        "edr": {
            "label": "Endpoint Detection & Response",
            "reason": "Detect suspicious activity on compromised endpoints."
        },
        "least_privilege": {
            "label": "Least Privilege",
            "reason": "Limit the permissions available to compromised accounts."
        },
        "segmentation": {
            "label": "Network Segmentation",
            "reason": "Restrict movement from exposed systems toward critical assets."
        }
    }

    recommendations = []

    for control in unique_controls:

        info = defence_map.get(
            control
        )

        if info:

            recommendations.append({
                "id": control,
                "label": info["label"],
                "reason": info["reason"]
            })

        else:

            recommendations.append({
                "id": control,
                "label": control.replace(
                    "_",
                    " "
                ).title(),
                "reason": "Apply this control to reduce the associated attack path."
            })

    if not paths:

        explanation = (
            "No reachable attack path was found "
            "between the selected assets."
        )

    else:

        explanation = (
            f"{len(paths)} reachable attack path"
            f"{'s' if len(paths) != 1 else ''} "
            f"were identified toward the selected "
            f"asset. The target has criticality "
            f"level {target_criticality}."
        )

    return {
        "source": source,
        "target": target,
        "path_count": len(paths),
        "paths": paths,
        "risk": risk,
        "mitre": mitre,
        "recommendations": recommendations,
        "analysis": {
            "target_criticality": target_criticality,
            "average_difficulty": round(
                average_difficulty,
                2
            ),
            "unique_techniques": len(
                unique_techniques
            ),
            "unique_controls": len(
                unique_controls
            ),
            "explanation": explanation
        }
    }


def get_twin_summary() -> dict:
    """Return basic information for the website."""

    twin = load_twin()

    return {
        "org": twin["org"],
        "nodes": len(
            twin["nodes"]
        ),
        "edges": len(
            twin["edges"]
        ),
        "controls": len(
            twin["controls"]
        )
    }