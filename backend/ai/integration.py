
import json

from .llm import explain_with_ai


def explain_edge_ids(path, twin):
    """
    Convert Shaju's edge IDs into AI explanation input.
    Return the frozen ExplainResponse format.
    """

    if not path:
        raise ValueError("Attack path cannot be empty")

    edges = {
        edge["id"]: edge
        for edge in twin.get("edges", [])
    }

    hops = []
    previous_target = None

    for edge_id in path:
        if edge_id not in edges:
            raise ValueError(
                f"Unknown attack edge: {edge_id}"
            )

        edge = edges[edge_id]

        if (
            previous_target is not None
            and edge["source"] != previous_target
        ):
            raise ValueError(
                "Attack edges are not connected"
            )

        hops.append({
            "edge_id": edge["id"],
            "source": edge["source"],
            "target": edge["target"],
            "relation": edge["relation"],
            "technique_id": edge["technique"]
        })

        previous_target = edge["target"]

    result = explain_with_ai(hops)

    return {
        "steps": [
            {
                "edge": step["edge_id"],
                "technique": step["technique_id"],
                "text": step["text"]
            }
            for step in result["steps"]
        ],
        "summary": result["summary"],
        "source": (
            "llm"
            if result.get("mode") == "ai"
            else "template"
        )
    }


if __name__ == "__main__":

    sample_twin = {
        "edges": [
            {
                "id": "e1",
                "source": "u_ravi",
                "target": "ws_hr01",
                "relation": "phishing-related compromise",
                "technique": "T1566"
            }
        ]
    }

    response = explain_edge_ids(
        ["e1"], sample_twin
    )

    print(json.dumps(
        response,
        indent=2,
        ensure_ascii=False
    ))
