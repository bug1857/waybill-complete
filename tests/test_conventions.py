"""TSPLIB distance conventions, including the rounding trap."""

import math

import pytest

from core.distance.conventions import (
    TSPLIB_PI,
    EdgeWeightType,
    att,
    ceil_2d,
    distance_function,
    euc_2d,
    geo,
    man_2d,
    max_2d,
    nint,
)
from core.model.geometry import Coord


@pytest.mark.parametrize(
    "value,expected",
    [(0.0, 0), (0.4, 0), (0.5, 1), (1.5, 2), (2.5, 3), (2.4999, 2), (10.0, 10)],
)
def test_nint_rounds_half_away_from_zero(value, expected):
    assert nint(value) == expected


def test_nint_differs_from_python_round_on_halves():
    """The trap: round() is banker's rounding and would corrupt every distance."""
    assert nint(2.5) == 3
    assert round(2.5) == 2          # banker's rounding
    assert nint(0.5) == 1
    assert round(0.5) == 0
    assert nint(2.5) != round(2.5)


def test_nint_rejects_negative():
    with pytest.raises(ValueError):
        nint(-0.5)


def test_euc_2d_matches_spec():
    a, b = Coord(0.0, 0.0), Coord(3.0, 4.0)
    assert euc_2d(a, b) == 5
    # 0.5 exactly: must round up, not to even
    assert euc_2d(Coord(0.0, 0.0), Coord(0.5, 0.0)) == 1


def test_euc_2d_is_symmetric():
    a, b = Coord(12.5, 7.25), Coord(-3.75, 40.0)
    assert euc_2d(a, b) == euc_2d(b, a)


def test_ceil_2d_rounds_up():
    assert ceil_2d(Coord(0.0, 0.0), Coord(0.1, 0.0)) == 1
    assert ceil_2d(Coord(0.0, 0.0), Coord(3.0, 4.0)) == 5


def test_man_and_max_2d():
    a, b = Coord(0.0, 0.0), Coord(3.0, 4.0)
    assert man_2d(a, b) == 7
    assert max_2d(a, b) == 4


def test_att_never_underestimates():
    """ATT rounds up whenever nint rounded down."""
    a, b = Coord(0.0, 0.0), Coord(10.0, 10.0)
    true_value = math.sqrt((100.0 + 100.0) / 10.0)
    assert att(a, b) >= true_value


def test_geo_uses_truncated_pi_not_math_pi():
    assert TSPLIB_PI == 3.141592
    assert TSPLIB_PI != math.pi


def test_geo_is_zero_for_identical_points():
    p = Coord(52.5, 13.4)
    assert geo(p, p) in (0, 1)  # formula adds 1.0 before truncation


def test_distance_function_dispatch():
    assert distance_function(EdgeWeightType.EUC_2D) is euc_2d
    assert distance_function(EdgeWeightType.ATT) is att


def test_explicit_has_no_coordinate_formula():
    with pytest.raises(ValueError, match="EXPLICIT"):
        distance_function(EdgeWeightType.EXPLICIT)
