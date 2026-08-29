"""Matrix validation, symmetry detection, and content hashing."""

import pytest

from bench.generators import random_asymmetric_tsp, random_euclidean_tsp
from core.distance.conventions import euc_2d
from core.distance.matrix import DistanceMatrix
from core.model.geometry import Coord
from core.model.units import Unit


def test_detects_symmetry():
    m = DistanceMatrix([0, 5, 5, 0], 2, Unit.METRES)
    assert m.is_symmetric


def test_detects_asymmetry():
    """One differing pair is enough -- this is what a one-way street looks like."""
    m = DistanceMatrix([0, 5, 7, 0], 2, Unit.METRES)
    assert not m.is_symmetric


def test_rejects_nonzero_diagonal():
    with pytest.raises(ValueError, match="diagonal"):
        DistanceMatrix([1, 5, 5, 0], 2, Unit.METRES)


def test_rejects_negative_entries():
    with pytest.raises(ValueError, match="non-negative"):
        DistanceMatrix([0, -5, 5, 0], 2, Unit.METRES)


def test_rejects_float_entries():
    """Integer arithmetic is load-bearing; floats must not slip in."""
    with pytest.raises(TypeError, match="must be int"):
        DistanceMatrix([0, 5.0, 5.0, 0], 2, Unit.METRES)


def test_rejects_wrong_length():
    with pytest.raises(ValueError, match="expected 9 entries"):
        DistanceMatrix([0, 1, 1, 0], 3, Unit.METRES)


def test_from_coords_builds_symmetric_euclidean():
    coords = [Coord(0, 0), Coord(3, 4), Coord(6, 8)]
    m = DistanceMatrix.from_coords(coords, euc_2d, Unit.TSPLIB)
    assert m.is_symmetric
    assert m.cost(0, 1) == 5
    assert m.cost(0, 2) == 10


def test_hash_is_deterministic():
    a = random_euclidean_tsp(10, seed=7).matrix
    b = random_euclidean_tsp(10, seed=7).matrix
    assert a.content_hash == b.content_hash


def test_hash_changes_with_content():
    a = random_euclidean_tsp(10, seed=7).matrix
    b = random_euclidean_tsp(10, seed=8).matrix
    assert a.content_hash != b.content_hash


def test_hash_distinguishes_units():
    a = DistanceMatrix([0, 5, 5, 0], 2, Unit.METRES)
    b = DistanceMatrix([0, 5, 5, 0], 2, Unit.SECONDS)
    assert a.content_hash != b.content_hash


def test_generated_asymmetric_instance_really_is_asymmetric():
    assert not random_asymmetric_tsp(8, seed=1).matrix.is_symmetric
