"""Objective functions.

Every function here returns an integer in the matrix's own unit. Nothing in this
module rounds, scales, or converts -- rounding happened once when the matrix was
built.
"""

from collections.abc import Sequence

from core.distance.matrix import DistanceMatrix
from core.model.instance import Instance
from core.model.solution import Route, Solution


def closed_tour_cost(matrix: DistanceMatrix, tour: Sequence[int]) -> int:
    """Cost of a cyclic tour visiting ``tour`` in order and returning to its start.

    This is the function that scores a published TSPLIB optimal tour, so it is
    the first thing the validation chain exercises.
    """
    if len(tour) < 2:
        return 0
    total = 0
    for a, b in zip(tour, tour[1:]):
        total += matrix.cost(a, b)
    return total + matrix.cost(tour[-1], tour[0])


def route_cost(instance: Instance, route: Route) -> int:
    """Cost of one route: depot -> customers in order -> depot."""
    if route.is_empty:
        return 0
    depot = instance.depot_index
    m = instance.matrix
    total = m.cost(depot, route.sequence[0])
    for a, b in zip(route.sequence, route.sequence[1:]):
        total += m.cost(a, b)
    return total + m.cost(route.sequence[-1], depot)


def solution_cost(instance: Instance, solution: Solution) -> int:
    """Total cost across every route."""
    return sum(route_cost(instance, r) for r in solution.routes)
