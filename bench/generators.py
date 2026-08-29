"""Random instance generation for property tests and sweeps.

Seeded and reproducible: the same seed yields the same instance, so a failing
property test can be replayed exactly. Instances that break an invariant should
still be promoted to named fixtures rather than left to a seed, because seeds
stop reproducing as soon as the generator changes.
"""

import random

from core.distance.conventions import euc_2d
from core.distance.matrix import DistanceMatrix
from core.model.geometry import Coord
from core.model.instance import Instance
from core.model.stop import Stop
from core.model.units import Unit


def random_euclidean_tsp(
    n: int,
    seed: int,
    span: float = 1000.0,
    name: str | None = None,
) -> Instance:
    """A symmetric Euclidean TSP instance on ``n`` nodes, depot at index 0."""
    if n < 1:
        raise ValueError("n must be at least 1")
    rng = random.Random(seed)
    coords = [Coord(rng.uniform(0, span), rng.uniform(0, span)) for _ in range(n)]
    matrix = DistanceMatrix.from_coords(coords, euc_2d, Unit.TSPLIB)
    stops = tuple(Stop(id=i, coord=c) for i, c in enumerate(coords))
    return Instance.single_vehicle_tsp(
        name=name or f"rand-euc-n{n}-s{seed}",
        stops=stops,
        matrix=matrix,
        metadata={"generator": "random_euclidean_tsp", "seed": str(seed)},
    )


def random_asymmetric_tsp(
    n: int,
    seed: int,
    low: int = 1,
    high: int = 999,
    name: str | None = None,
) -> Instance:
    """An asymmetric TSP instance where ``d(i,j)`` and ``d(j,i)`` differ.

    Used to exercise the paths that must not assume symmetry -- notably the
    brute-force reversal reduction, which must switch itself off here.
    """
    if n < 1:
        raise ValueError("n must be at least 1")
    rng = random.Random(seed)
    data = [0] * (n * n)
    for i in range(n):
        for j in range(n):
            if i != j:
                data[i * n + j] = rng.randint(low, high)
    matrix = DistanceMatrix(data, n, Unit.TSPLIB)
    stops = tuple(Stop(id=i) for i in range(n))
    return Instance.single_vehicle_tsp(
        name=name or f"rand-asym-n{n}-s{seed}",
        stops=stops,
        matrix=matrix,
        metadata={"generator": "random_asymmetric_tsp", "seed": str(seed)},
    )
