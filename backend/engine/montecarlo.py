
import numpy as np

from .graph import hop_p


def breach_probability(
    G,
    entries,
    jewels,
    persona,
    runs=5000,
    seed=42
):
    if not entries:
        return 0.0

    if runs <= 0:
        raise ValueError("runs must be positive")

    rng = np.random.default_rng(seed)

    jewels = set(jewels)
    hits = 0

    for _ in range(runs):
        start = entries[rng.integers(len(entries))]

        seen = {start}
        frontier = [start]

        while frontier:
            nxt = []

            for u in frontier:
                for v in G.successors(u):
                    if v not in seen:
                        probability = hop_p(
                            G[u][v],
                            persona
                        )

                        if rng.random() < probability:
                            seen.add(v)
                            nxt.append(v)

            frontier = nxt

        hits += bool(seen & jewels)

    return round(
        hits / runs * 100,
        1
    )
