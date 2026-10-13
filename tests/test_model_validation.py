"""Domain objects reject values Python would otherwise coerce or wrap."""

import pytest

from core.distance.matrix import DistanceMatrix
from core.model.instance import Instance
from core.model.solution import Route, Solution
from core.model.stop import Stop, TimeWindow
from core.model.units import Unit
from core.model.vehicle import Vehicle
from core.solver import Budget


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Stop(id=True),
        lambda: Stop(id=0, demand=1.5),
        lambda: Stop(id=0, service_time=2.5),
        lambda: TimeWindow(False, 10),
        lambda: Vehicle(id=True),
        lambda: Vehicle(id=0, capacity=1.5),
        lambda: Vehicle(id=0, shift_start=0.5),
        lambda: Route(vehicle_id=True, sequence=(1,)),
        lambda: Route(vehicle_id=0, sequence=(True,)),
        lambda: Solution(routes=(), unserved=frozenset({True})),
        lambda: Budget(max_nodes=True),
    ],
)
def test_integer_domain_fields_reject_bool_and_float(factory):
    with pytest.raises(TypeError):
        factory()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Stop(id=-1),
        lambda: Vehicle(id=-1),
        lambda: Route(vehicle_id=-1, sequence=()),
        lambda: Route(vehicle_id=0, sequence=(-1,)),
        lambda: Solution(routes=(), unserved=frozenset({-1})),
    ],
)
def test_identifier_and_index_domains_reject_negative_values(factory):
    with pytest.raises(ValueError):
        factory()


def test_instance_requires_unique_stop_ids():
    matrix = DistanceMatrix([0, 1, 1, 0], 2, Unit.METRES)
    with pytest.raises(ValueError, match="stop ids must be unique"):
        Instance.single_vehicle_tsp(
            "duplicate-ids", (Stop(7), Stop(7)), matrix
        )


def test_instance_rejects_boolean_depot_index():
    matrix = DistanceMatrix([0], 1, Unit.METRES)
    with pytest.raises(TypeError, match="depot_index"):
        Instance.single_vehicle_tsp("bad-depot", (Stop(0),), matrix, True)
