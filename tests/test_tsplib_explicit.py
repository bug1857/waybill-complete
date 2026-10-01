"""Regression tests for TSPLIB EXPLICIT matrix encodings."""

from pathlib import Path

import pytest

from bench.tsplib.parser import parse_problem


def _write_problem(
    path: Path,
    *,
    problem_type: str = "TSP",
    dimension: int = 4,
    weight_format: str,
    weights: str,
) -> Path:
    path.write_text(
        "\n".join(
            (
                "NAME: explicit-fixture",
                f"TYPE: {problem_type}",
                f"DIMENSION: {dimension}",
                "EDGE_WEIGHT_TYPE: EXPLICIT",
                f"EDGE_WEIGHT_FORMAT: {weight_format}",
                "EDGE_WEIGHT_SECTION",
                weights,
                "EOF",
            )
        ),
        encoding="utf-8",
    )
    return path


def test_full_matrix_preserves_asymmetry(tmp_path: Path) -> None:
    path = _write_problem(
        tmp_path / "directed.tsp",
        problem_type="ATSP",
        dimension=3,
        weight_format="FULL_MATRIX",
        weights="0 2 9\n7 0 3\n4 8 0",
    )

    problem = parse_problem(path)
    instance = problem.to_instance()

    assert problem.dimension == 3
    assert problem.coords == ()
    assert instance.matrix.cost(0, 1) == 2
    assert instance.matrix.cost(1, 0) == 7
    assert not instance.matrix.is_symmetric


@pytest.mark.parametrize(
    ("weight_format", "weights"),
    (
        ("UPPER_ROW", "2 3 4 5 6 7"),
        ("LOWER_ROW", "2 3 5 4 6 7"),
        ("UPPER_DIAG_ROW", "0 2 3 4 0 5 6 0 7 0"),
        ("LOWER_DIAG_ROW", "0 2 0 3 5 0 4 6 7 0"),
        ("UPPER_COL", "2 3 5 4 6 7"),
        ("LOWER_COL", "2 3 4 5 6 7"),
        ("UPPER_DIAG_COL", "0 2 0 3 5 0 4 6 7 0"),
        ("LOWER_DIAG_COL", "0 2 3 4 0 5 6 0 7 0"),
    ),
)
def test_triangular_formats_decode_to_same_matrix(
    tmp_path: Path, weight_format: str, weights: str
) -> None:
    path = _write_problem(
        tmp_path / f"{weight_format.lower()}.tsp",
        weight_format=weight_format,
        weights=weights,
    )

    matrix = parse_problem(path).to_instance().matrix

    assert matrix.is_symmetric
    assert [[matrix.cost(i, j) for j in range(4)] for i in range(4)] == [
        [0, 2, 3, 4],
        [2, 0, 5, 6],
        [3, 5, 0, 7],
        [4, 6, 7, 0],
    ]


def test_explicit_requires_dimension_and_format(tmp_path: Path) -> None:
    missing_dimension = tmp_path / "missing-dimension.tsp"
    missing_dimension.write_text(
        "NAME: bad\nTYPE: TSP\nEDGE_WEIGHT_TYPE: EXPLICIT\n"
        "EDGE_WEIGHT_FORMAT: FULL_MATRIX\nEDGE_WEIGHT_SECTION\n0\nEOF\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="DIMENSION"):
        parse_problem(missing_dimension)

    missing_format = tmp_path / "missing-format.tsp"
    missing_format.write_text(
        "NAME: bad\nTYPE: TSP\nDIMENSION: 1\nEDGE_WEIGHT_TYPE: EXPLICIT\n"
        "EDGE_WEIGHT_SECTION\n0\nEOF\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="EDGE_WEIGHT_FORMAT"):
        parse_problem(missing_format)


def test_explicit_rejects_wrong_entry_count(tmp_path: Path) -> None:
    path = _write_problem(
        tmp_path / "truncated.tsp",
        dimension=3,
        weight_format="UPPER_ROW",
        weights="1 2",
    )
    with pytest.raises(ValueError, match="expected 3 edge weights, found 2"):
        parse_problem(path)


def test_explicit_rejects_unsupported_format(tmp_path: Path) -> None:
    path = _write_problem(
        tmp_path / "unsupported.tsp",
        dimension=2,
        weight_format="FUNCTION",
        weights="0 1 1 0",
    )
    with pytest.raises(ValueError, match="unsupported EDGE_WEIGHT_FORMAT"):
        parse_problem(path)
