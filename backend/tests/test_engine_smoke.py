
from engine.graph import (
    load_twin,
    active_graph,
    top_paths,
    blast_radius,
)
from engine.montecarlo import breach_probability
from engine.defend import plan

from models import Twin


def main():
    print("=" * 55)
    print("SHADOWTWIN - ENGINE SMOKE TEST")
    print("=" * 55)

    # 1. Load and validate organization data
    twin = load_twin()

    validated_twin = Twin.model_validate(twin)

    print("\n[PASS] Twin schema validated")
    print("Organization:", validated_twin.org)

    # 2. Identify enabled controls
    enabled_controls = {
        c["id"]
        for c in twin["controls"]
        if c.get("enabled", False)
    }

    # 3. Build attack graph
    G = active_graph(twin, enabled_controls)

    # 4. Get entry points from props.entry
    entries = [
        n["id"]
        for n in twin["nodes"]
        if n.get("props", {}).get("entry", False)
    ]

    # 5. Get crown jewels from props.crown_jewel
    jewels = [
        n["id"]
        for n in twin["nodes"]
        if n.get("props", {}).get("crown_jewel", False)
    ]

    print("\n--- GRAPH INFORMATION ---")
    print("Nodes:", G.number_of_nodes())
    print("Edges:", G.number_of_edges())
    print("Enabled controls:", sorted(enabled_controls))
    print("Entries:", entries)
    print("Crown jewels:", jewels)

    if not entries or not jewels:
        print("\n[FAIL] Missing entry or crown jewel")
        return

    # 6. Find top attack paths
    print("\n--- TOP ATTACK PATHS ---")

    all_paths = []

    for entry in entries:
        for jewel in jewels:
            paths = top_paths(
                G,
                entry,
                jewel,
                "apt",
                k=5
            )
            all_paths.extend(paths)

    all_paths = sorted(
        all_paths,
        key=lambda x: -x["likelihood"]
    )[:5]

    if all_paths:
        for index, path in enumerate(all_paths, start=1):
            print(f"\nPath {index}")
            print("Nodes:", " -> ".join(path["nodes"]))
            print("Edges:", path["edges"])
            print("Likelihood:", path["likelihood"])
    else:
        print("No active attack paths found.")

    # 7. Calculate blast radius
    print("\n--- BLAST RADIUS ---")

    for entry in entries:
        blast = blast_radius(G, entry)

        print("Entry:", entry)
        print("Reachable assets:", blast["assets"])
        print("Criticality score:", blast["score"])

    # 8. Monte Carlo breach simulation
    print("\n--- MONTE CARLO SIMULATION ---")

    for persona in [
        "script_kiddie",
        "ransomware",
        "apt"
    ]:
        probability = breach_probability(
            G,
            entries,
            jewels,
            persona,
            runs=5000,
            seed=42
        )

        print(f"{persona}: {probability}%")

    # 9. Defence recommendation
    print("\n--- DEFENCE PLANNER ---")

    result = plan(
        twin,
        entries,
        jewels,
        "apt",
        budget=2
    )

    print("Before defence:", result["before"], "%")

    for index, step in enumerate(result["steps"], start=1):
        print(f"\nDefence step {index}")
        print("Control:", step["control"])
        print("Breach after:", step["breach_after"], "%")

    print("\nSelected controls:", result["controls"])

    # 10. Completion
    print("\n" + "=" * 55)
    print("SHADOWTWIN ENGINE SMOKE TEST COMPLETED")
    print("=" * 55)


if __name__ == "__main__":
    main()
