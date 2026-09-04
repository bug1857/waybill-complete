"""The reduced-cost lower bound (Little et al., 1963).

The textbook Branch & Bound bound, and the one this project's assignment names.

Any completion of a partial tour must give every not-yet-departed node exactly
one outgoing edge, and every not-yet-entered node exactly one incoming edge. So:

1. **Row reduction** -- for each node still needing an outgoing edge, take the
   cheapest edge available to it. Their sum is a lower bound on the outgoing
   cost, because each of those edges must be paid for by *something*.
2. **Column reduction** -- subtract the row minima, then for each node still
   needing an incoming edge take the cheapest remaining entry. That residual is
   cost the row bound has not already counted.

Their sum is a valid lower bound on completing the tour.

**Validity is the only thing that matters here.** A bound that is too high does
not raise -- it prunes the branch containing the optimum and returns a confident
wrong answer stamped as proven. The invariant test in the suite exists solely to
catch that, and any new bound must pass it before being used.
"""

from collections.abc import Collection

from core.distance.matrix import DistanceMatrix

INF = float("inf")


def completion_bound(
    matrix: DistanceMatrix,
    last: int,
    unvisited: Collection[int],
    depot: int,
) -> int:
    """Lower bound on finishing a tour: ``last`` -> all of ``unvisited`` -> ``depot``.

    Returns 0 when nothing is left to bound beyond the direct return leg, which
    the caller accounts for separately.
    """
    if not unvisited:
        return matrix.cost(last, depot)

    remaining = list(unvisited)

    # Nodes that still need an outgoing edge, and what they may go to.
    out_rows = [last, *remaining]
    # Nodes that still need an incoming edge.
    in_cols = [*remaining, depot]

    row_min: dict[int, int] = {}
    total = 0
    for r in out_rows:
        best = INF
        for c in in_cols:
            if c == r:
                continue
            cost = matrix.cost(r, c)
            if cost < best:
                best = cost
        if best == INF:
            return 0
        row_min[r] = best
        total += best

    for c in in_cols:
        best = INF
        for r in out_rows:
            if c == r:
                continue
            residual = matrix.cost(r, c) - row_min[r]
            if residual < best:
                best = residual
        if best == INF:
            continue
        if best > 0:
            total += best

    return int(total)
