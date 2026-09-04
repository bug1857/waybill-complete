"""Explicit edge-weight matrices.

Many classic TSPLIB instances define distances as a literal matrix rather than
as geometry. Their files often also carry a ``DISPLAY_DATA_SECTION`` holding
coordinates -- but those exist only for drawing, and applying a Euclidean
formula to them produces a different problem.

That is not a hypothetical error. A parallel implementation of this project did
exactly that with ``bayg29``: it read the display coordinates, applied EUC_2D,
and paired the result with the real instance's published optimum of 1610. The
two distance models differ by a factor of about six, and the resulting benchmark
reported a 621% nearest-neighbour gap as though it were a finding.

So this module exists to make the correct path available, and the parser refuses
to fall back to display coordinates when a matrix is declared.

Layouts, all row-wise (the column variants are rarer and rejected explicitly):

``FULL_MATRIX``      all n*n entries
``UPPER_ROW``        strict upper triangle, n(n-1)/2 entries
``LOWER_ROW``        strict lower triangle, n(n-1)/2 entries
``UPPER_DIAG_ROW``   upper triangle including diagonal, n(n+1)/2 entries
``LOWER_DIAG_ROW``   lower triangle including diagonal, n(n+1)/2 entries
"""

from collections.abc import Sequence
from enum import StrEnum


class EdgeWeightFormat(StrEnum):
    FULL_MATRIX = "FULL_MATRIX"
    UPPER_ROW = "UPPER_ROW"
    LOWER_ROW = "LOWER_ROW"
    UPPER_DIAG_ROW = "UPPER_DIAG_ROW"
    LOWER_DIAG_ROW = "LOWER_DIAG_ROW"


def expected_entry_count(fmt: EdgeWeightFormat, n: int) -> int:
    """How many numbers a well-formed section should contain."""
    if fmt is EdgeWeightFormat.FULL_MATRIX:
        return n * n
    if fmt in (EdgeWeightFormat.UPPER_ROW, EdgeWeightFormat.LOWER_ROW):
        return n * (n - 1) // 2
    return n * (n + 1) // 2


def _index_pairs(fmt: EdgeWeightFormat, n: int):
    """Yield (i, j) in the order the format lists them."""
    if fmt is EdgeWeightFormat.FULL_MATRIX:
        for i in range(n):
            for j in range(n):
                yield i, j
    elif fmt is EdgeWeightFormat.UPPER_ROW:
        for i in range(n):
            for j in range(i + 1, n):
                yield i, j
    elif fmt is EdgeWeightFormat.UPPER_DIAG_ROW:
        for i in range(n):
            for j in range(i, n):
                yield i, j
    elif fmt is EdgeWeightFormat.LOWER_ROW:
        for i in range(n):
            for j in range(i):
                yield i, j
    elif fmt is EdgeWeightFormat.LOWER_DIAG_ROW:
        for i in range(n):
            for j in range(i + 1):
                yield i, j
    else:  # pragma: no cover - guarded by the enum
        raise ValueError(f"unsupported edge weight format: {fmt}")


def build_matrix_data(
    values: Sequence[float], fmt: EdgeWeightFormat, n: int
) -> list[int]:
    """Expand a TSPLIB weight section into a flat ``n*n`` row-major matrix.

    Triangular layouts are mirrored, since a triangle can only describe a
    symmetric instance. ``FULL_MATRIX`` is taken as given and may be asymmetric.
    """
    expected = expected_entry_count(fmt, n)
    if len(values) != expected:
        raise ValueError(
            f"{fmt.value} with n={n} needs {expected} entries, got {len(values)}"
        )

    data = [0] * (n * n)
    mirror = fmt is not EdgeWeightFormat.FULL_MATRIX

    for value, (i, j) in zip(values, _index_pairs(fmt, n)):
        weight = int(value)
        if weight < 0:
            raise ValueError(f"negative edge weight {weight} at ({i},{j})")
        data[i * n + j] = weight
        if mirror:
            data[j * n + i] = weight

    # A declared diagonal is sometimes non-zero in the wild; the distance from a
    # node to itself is zero by definition, so normalise rather than reject.
    for i in range(n):
        data[i * n + i] = 0

    return data
