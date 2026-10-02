"""The Phase 0 exit gate.

Scoring a published optimal tour with our own distance implementation must
reproduce the published optimal length exactly. Two independent facts -- an
externally published number, and a number this project computes -- have to agree.

If they disagree the failure message shows both, because the cause is either a
wrong distance convention or a wrong tour parser, and the difference between
those two is what the numbers reveal.

This test guards every gap figure the project will ever report: a distance
convention that is off by a rounding rule produces tours a percent or two above
published optima, which is indistinguishable from a mediocre solver.
"""

from pathlib import Path

import pytest

from bench.tsplib.known_optima import PUBLISHED_OPTIMA
from bench.tsplib.parser import parse_problem, parse_tour
from core.eval.objective import closed_tour_cost

DATA = Path(__file__).resolve().parent.parent / "data" / "tsplib"

INSTANCES = sorted(PUBLISHED_OPTIMA)


@pytest.mark.parametrize("name", INSTANCES)
def test_instance_file_parses(name):
    problem = parse_problem(DATA / f"{name}.tsp")
    assert problem.name.lower().startswith(name.lower()[:4])
    assert problem.dimension == len(problem.coords)
    assert problem.dimension > 0


@pytest.mark.parametrize("name", INSTANCES)
def test_optimal_tour_visits_every_node_once(name):
    problem = parse_problem(DATA / f"{name}.tsp")
    tour = parse_tour(DATA / f"{name}.opt.tour")
    assert len(tour) == problem.dimension
    assert set(tour) == set(range(problem.dimension))


@pytest.mark.parametrize("name", INSTANCES)
def test_published_optimum_is_reproduced(name):
    """THE EXIT GATE. Our scoring of the published tour must equal the published cost."""
    instance = parse_problem(DATA / f"{name}.tsp").to_instance()
    tour = parse_tour(DATA / f"{name}.opt.tour")
    computed = closed_tour_cost(instance.matrix, tour)
    published = PUBLISHED_OPTIMA[name]
    assert computed == published, (
        f"{name}: computed {computed}, published {published} "
        f"(difference {computed - published}, {abs(computed - published) / published:.4%}). "
        f"A mismatch means the distance convention or the tour parser is wrong."
    )


@pytest.mark.parametrize("name", INSTANCES)
def test_tour_cost_is_rotation_invariant(name):
    """A cyclic tour costs the same wherever you start reading it."""
    instance = parse_problem(DATA / f"{name}.tsp").to_instance()
    tour = parse_tour(DATA / f"{name}.opt.tour")
    base = closed_tour_cost(instance.matrix, tour)
    for shift in (1, 7, len(tour) - 1):
        rotated = tour[shift:] + tour[:shift]
        assert closed_tour_cost(instance.matrix, rotated) == base


@pytest.mark.parametrize("name", INSTANCES)
def test_tour_cost_is_reversal_invariant_when_symmetric(name):
    """Reversal is free only because these instances are symmetric (see core/local)."""
    instance = parse_problem(DATA / f"{name}.tsp").to_instance()
    assert instance.matrix.is_symmetric
    tour = parse_tour(DATA / f"{name}.opt.tour")
    assert closed_tour_cost(instance.matrix, tour) == closed_tour_cost(
        instance.matrix, tuple(reversed(tour))
    )


@pytest.mark.parametrize("name", INSTANCES)
def test_matrix_hash_is_stable_across_builds(name):
    a = parse_problem(DATA / f"{name}.tsp").to_instance()
    b = parse_problem(DATA / f"{name}.tsp").to_instance()
    assert a.matrix.content_hash == b.matrix.content_hash


def test_distinct_instances_hash_differently():
    a = parse_problem(DATA / "berlin52.tsp").to_instance()
    b = parse_problem(DATA / "eil51.tsp").to_instance()
    assert a.matrix.content_hash != b.matrix.content_hash


@pytest.mark.parametrize("bad_id", ["0", "-2"])
def test_tour_parser_rejects_non_positive_node_ids(tmp_path, bad_id):
    path = tmp_path / "bad.opt.tour"
    path.write_text(f"TOUR_SECTION\n1\n{bad_id}\n-1\nEOF\n")
    with pytest.raises(ValueError, match="node ids must be positive"):
        parse_tour(path)


def test_problem_parser_rejects_non_positive_dimension(tmp_path):
    path = tmp_path / "bad.tsp"
    path.write_text(
        "NAME: bad\nTYPE: TSP\nDIMENSION: 0\n"
        "EDGE_WEIGHT_TYPE: EUC_2D\nNODE_COORD_SECTION\nEOF\n"
    )
    with pytest.raises(ValueError, match="DIMENSION must be positive"):
        parse_problem(path)
