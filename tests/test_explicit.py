"""EXPLICIT edge-weight instances.

The trap this guards: many classic TSPLIB instances define distances as a
matrix and *also* carry coordinates for drawing. Applying a Euclidean formula to
those display coordinates produces a different problem. A parallel
implementation did exactly that with bayg29 and was 6.07x out, reporting a 621%
nearest-neighbour gap as a finding.
"""

from pathlib import Path

import pytest

from bench.tsplib.parser import parse_problem, parse_tour
from core.distance.explicit import (
    EdgeWeightFormat,
    build_matrix_data,
    expected_entry_count,
)
from core.eval.objective import closed_tour_cost

DATA = Path(__file__).resolve().parent.parent / "data" / "tsplib"

#: Published optima. Cross-checked below by scoring the real .opt.tour files.
EXPLICIT_OPTIMA = {"gr24": 1272, "bayg29": 1610, "bays29": 2020}


@pytest.mark.parametrize("name,expected", sorted(EXPLICIT_OPTIMA.items()))
def test_explicit_instance_reproduces_published_optimum(name, expected):
    instance = parse_problem(DATA / f"{name}.tsp").to_instance()
    tour = parse_tour(DATA / f"{name}.opt.tour")
    computed = closed_tour_cost(instance.matrix, tour)
    assert computed == expected, (
        f"{name}: computed {computed}, published {expected}. The explicit matrix "
        f"was parsed wrongly, or display coordinates leaked into the distances."
    )


@pytest.mark.parametrize("name", sorted(EXPLICIT_OPTIMA))
def test_explicit_instances_expose_no_geometry(name):
    """Display coordinates must never be usable as geometry."""
    problem = parse_problem(DATA / f"{name}.tsp")
    assert problem.is_explicit
    assert problem.coords == (), (
        "an EXPLICIT instance must expose no geometric coordinates; its display "
        "data is for drawing only"
    )


def test_display_data_is_still_available_for_drawing():
    problem = parse_problem(DATA / "bayg29.tsp")
    assert len(problem.display_coords) == 29
    instance = problem.to_instance()
    assert instance.stops[3].coord is not None


def test_all_three_row_formats_are_covered_by_the_fixtures():
    formats = {
        parse_problem(DATA / f"{n}.tsp").edge_weight_format for n in EXPLICIT_OPTIMA
    }
    assert formats == {
        EdgeWeightFormat.LOWER_DIAG_ROW,
        EdgeWeightFormat.UPPER_ROW,
        EdgeWeightFormat.FULL_MATRIX,
    }


@pytest.mark.parametrize(
    "fmt,n,expected",
    [
        (EdgeWeightFormat.FULL_MATRIX, 4, 16),
        (EdgeWeightFormat.UPPER_ROW, 4, 6),
        (EdgeWeightFormat.LOWER_ROW, 4, 6),
        (EdgeWeightFormat.UPPER_DIAG_ROW, 4, 10),
        (EdgeWeightFormat.LOWER_DIAG_ROW, 4, 10),
    ],
)
def test_expected_entry_counts(fmt, n, expected):
    assert expected_entry_count(fmt, n) == expected


def test_upper_row_expands_and_mirrors():
    # n=3, upper triangle: (0,1)=5, (0,2)=9, (1,2)=4
    data = build_matrix_data([5, 9, 4], EdgeWeightFormat.UPPER_ROW, 3)
    assert data == [0, 5, 9, 5, 0, 4, 9, 4, 0]


def test_lower_diag_row_expands_and_mirrors():
    # n=3, lower triangle with diagonal: (0,0)=0 (1,0)=5 (1,1)=0 (2,0)=9 (2,1)=4 (2,2)=0
    data = build_matrix_data([0, 5, 0, 9, 4, 0], EdgeWeightFormat.LOWER_DIAG_ROW, 3)
    assert data == [0, 5, 9, 5, 0, 4, 9, 4, 0]


def test_full_matrix_preserves_asymmetry():
    data = build_matrix_data([0, 5, 7, 0], EdgeWeightFormat.FULL_MATRIX, 2)
    assert data == [0, 5, 7, 0]      # not mirrored


def test_wrong_entry_count_is_rejected():
    with pytest.raises(ValueError, match="needs 6 entries, got 3"):
        build_matrix_data([1, 2, 3], EdgeWeightFormat.UPPER_ROW, 4)


def test_nonzero_diagonal_is_normalised():
    data = build_matrix_data([9, 5, 9, 9, 4, 9], EdgeWeightFormat.LOWER_DIAG_ROW, 3)
    assert data[0] == 0 and data[4] == 0 and data[8] == 0
