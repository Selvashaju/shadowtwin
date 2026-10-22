
import json
from pathlib import Path

MITRE_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "mitre_techniques.json"
)


def load_techniques():
    with open(MITRE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def explain_path(hops):
    """
    Explain attack transitions produced by the simulation engine.
    This baseline works without an AI API key.
    """
    techniques = load_techniques()

    if isinstance(hops, dict):
        hops = hops.get("hops", [])

    if not isinstance(hops, list) or not hops:
        raise ValueError("A non-empty list of attack hops is required")

    steps = []
    recommendations = []

    for hop in hops:
        edge_id = hop.get("edge_id") or hop.get("id")
        technique_id = (
            hop.get("technique_id") or hop.get("technique")
        )

        if not edge_id or not technique_id:
            raise ValueError("Each hop needs an edge and technique ID")

        source = hop.get("source") or hop.get("from", "Unknown")
        target = hop.get("target") or hop.get("to", "Unknown")
        relation = hop.get("relation", "potential attack access")

        technique = techniques.get(technique_id)

        if technique:
            explanation = (
                f"Edge {edge_id} | MITRE {technique_id} "
                f"({technique['name']}): "
                f"The simulated attacker may move from "
                f"{source} to {target} through {relation}. "
                f"{technique['description']}"
            )
            recommendations.append(technique["defense"])
        else:
            explanation = (
                f"Edge {edge_id} | Technique {technique_id}: "
                f"Potential transition from {source} to {target}. "
                f"This technique needs verification."
            )

        steps.append({
            "edge_id": edge_id,
            "technique_id": technique_id,
            "text": explanation
        })

    unique_fixes = list(dict.fromkeys(recommendations))

    return {
        "summary": (
            f"The simulation identified a potential "
            f"attack path containing {len(steps)} transitions."
        ),
        "steps": steps,
        "top_fix": (
            "; ".join(unique_fixes[:2])
            if unique_fixes
            else "Review the modeled attack relationships"
        )
    }


if __name__ == "__main__":
    sample_hops = [
        {
            "edge_id": "e1",
            "source": "u_ravi",
            "target": "ws_hr01",
            "relation": "phishing-related compromise",
            "technique_id": "T1566"
        },
        {
            "edge_id": "e2",
            "source": "ws_hr01",
            "target": "app_hrms",
            "relation": "web session exposure",
            "technique_id": "T1539"
        },
        {
            "edge_id": "e3",
            "source": "app_hrms",
            "target": "srv_ad",
            "relation": "account access",
            "technique_id": "T1078"
        }
    ]

    result = explain_path(sample_hops)
    print(json.dumps(result, indent=2, ensure_ascii=False))
