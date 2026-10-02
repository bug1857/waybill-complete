"""Random instance generation for property tests and sweeps.

Seeded and reproducible: the same seed yields the same instance, so a failing
property test can be replayed exactly. Instances that break an invariant should
still be promoted to named fixtures rather than left to a seed, because seeds
stop reproducing as soon as the generator changes.
"""

import math
import random

from core.distance.conventions import euc_2d
from core.distance.matrix import DistanceMatrix
from core.model.geometry import Coord
from core.model.instance import Instance
from core.model.stop import Stop, TimeWindow
from core.model.units import Unit
from core.model.vehicle import Vehicle


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


def clustered_cvrptw_150(seed: int = 240519) -> Instance:
    """Return the named 150-customer, six-vehicle Phase 5 gate instance.

    Six spatial clusters model delivery territories around one depot. Every
    parcel has a service duration and a hard shift-bounded window; early arrival
    is allowed and produces waiting. The generator identity and seed live in the
    instance metadata, while both generated matrices receive stable content
    hashes from :class:`DistanceMatrix`.

    This is a reproducible synthetic integration fixture, not a claim about a
    particular city's roads or traffic.
    """
    customer_count = 150
    vehicle_count = 6
    customers_per_vehicle = customer_count // vehicle_count
    shift_end = 8 * 60 * 60
    rng = random.Random(seed)

    coords: list[Coord] = [Coord(0.0, 0.0)]
    stops: list[Stop] = [Stop(id=0, coord=coords[0])]
    next_id = 1

    for cluster in range(vehicle_count):
        angle = 2.0 * math.pi * cluster / vehicle_count
        centre_x = 8_000.0 * math.cos(angle)
        centre_y = 8_000.0 * math.sin(angle)
        for local_index in range(customers_per_vehicle):
            # A bounded disc-like jitter keeps territories distinct without
            # putting every point on an artificial grid.
            jitter_angle = rng.uniform(0.0, 2.0 * math.pi)
            jitter_radius = rng.uniform(150.0, 1_350.0)
            coord = Coord(
                centre_x + jitter_radius * math.cos(jitter_angle),
                centre_y + jitter_radius * math.sin(jitter_angle),
            )
            coords.append(coord)
            earliest = (local_index % 5) * 5 * 60
            stops.append(
                Stop(
                    id=next_id,
                    coord=coord,
                    demand=1,
                    time_window=TimeWindow(earliest, 7 * 60 * 60),
                    service_time=2 * 60,
                )
            )
            next_id += 1

    cost_matrix = DistanceMatrix.from_coords(coords, euc_2d, Unit.METRES)
    time_data: list[int] = []
    for i in range(len(coords)):
        for j in range(len(coords)):
            metres = cost_matrix.cost(i, j)
            # Static 10 m/s planning speed, rounded upward to whole seconds.
            time_data.append(0 if i == j else max(1, (metres + 9) // 10))
    time_matrix = DistanceMatrix(time_data, len(coords), Unit.SECONDS)

    vehicles = tuple(
        Vehicle(
            id=vehicle_id,
            capacity=customers_per_vehicle,
            shift_start=0,
            shift_end=shift_end,
            max_route_duration=shift_end,
        )
        for vehicle_id in range(vehicle_count)
    )
    return Instance(
        name=f"clustered-cvrptw-c150-v6-s{seed}",
        stops=tuple(stops),
        vehicles=vehicles,
        matrix=cost_matrix,
        time_matrix=time_matrix,
        metadata={
            "generator": "clustered_cvrptw_150",
            "seed": str(seed),
            "customer_count": str(customer_count),
            "vehicle_count": str(vehicle_count),
            "planning_speed_mps": "10",
            "claim_scope": "synthetic reproducible integration fixture",
        },
    )
