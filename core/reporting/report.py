"""The SolveReport contract.

Every solver returns one of these. The validation in ``__post_init__`` is the
claim discipline made mechanical: a report that claims proven optimality without
a proof condition, or supplies a reference value with no provenance, cannot be
constructed at all.

The benchmark harness refuses to plot a run whose mandatory fields are missing,
so a figure in the report always traces back to a complete record.
"""

from dataclasses import dataclass, field

from core.model.instance import ProblemType
from core.model.units import Unit
from core.reporting.status import SolveStatus, StopReason


@dataclass(frozen=True, slots=True)
class SolveReport:
    """What a solver knows about the answer it just produced."""

    solver_name: str
    problem_type: ProblemType
    status: SolveStatus
    stop_reason: StopReason
    objective_value: int
    objective_units: Unit

    # Proof, when an exact search exposes one.
    best_lower_bound: int | None = None

    # External comparison. Provenance is mandatory whenever a value is given.
    reference_value: int | None = None
    reference_source: str | None = None

    # Cost of getting here.
    wall_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    peak_memory_mb: float | None = None

    # Branch & Bound instrumentation.
    nodes_created: int = 0
    nodes_explored: int = 0
    nodes_pruned: int = 0
    peak_frontier: int = 0
    bound_time_ms: float = 0.0

    # Reproducibility.
    seed: int | None = None
    solver_config_hash: str | None = None
    distance_matrix_hash: str | None = None
    hardware_id: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.objective_value < 0:
            raise ValueError("objective_value must be non-negative")

        if self.status.permits_word_optimal:
            if self.stop_reason is not StopReason.OPTIMAL:
                raise ValueError(
                    f"{self.status.value} requires stop_reason=OPTIMAL, "
                    f"got {self.stop_reason.value}. A solver that stopped for any "
                    f"other reason has not proven anything."
                )
            if self.problem_type is not ProblemType.TSP:
                raise ValueError(
                    f"{self.status.value} is only valid for TSP; this run was "
                    f"{self.problem_type.value}. A TSP optimality certificate says "
                    f"nothing about a multi-vehicle plan."
                )

        if self.status is SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT:
            if self.best_lower_bound is None:
                raise ValueError(
                    "EXACT_TIMEOUT_WITH_INCUMBENT must carry best_lower_bound, "
                    "otherwise the residual gap is unknown and the run is unusable"
                )

        if self.reference_value is not None and not self.reference_source:
            raise ValueError(
                "reference_value requires reference_source: an unattributed "
                "comparator cannot be checked by anyone"
            )

        if self.best_lower_bound is not None:
            if self.best_lower_bound < 0:
                raise ValueError("best_lower_bound must be non-negative")
            if self.best_lower_bound > self.objective_value:
                raise ValueError(
                    f"lower bound {self.best_lower_bound} exceeds objective "
                    f"{self.objective_value}: the bound is invalid, and an invalid "
                    f"bound may already have pruned the optimum"
                )

    @property
    def proven_gap(self) -> float | None:
        """``(incumbent - lower_bound) / incumbent``, or None if unprovable.

        Only defined when a valid lower bound exists. This is the only gap this
        project is entitled to call an *optimality* gap.
        """
        if self.best_lower_bound is None or self.objective_value == 0:
            return None
        return (self.objective_value - self.best_lower_bound) / self.objective_value

    @property
    def reference_gap(self) -> float | None:
        """``(objective - reference) / reference``. Not an optimality gap.

        Named separately because the comparator is a heuristic or a published
        value, not a proof produced by this run.
        """
        if self.reference_value is None or self.reference_value == 0:
            return None
        return (self.objective_value - self.reference_value) / self.reference_value

    def headline(self) -> str:
        """A one-line description no stronger than the status permits.

        UI and report code should call this rather than composing their own
        wording, so the claim rules live in one place.
        """
        base = f"{self.objective_value} {self.objective_units.value}"
        if self.status.permits_word_optimal:
            return f"{base} (optimal for this TSP instance)"
        if self.status is SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT:
            gap = self.proven_gap
            pct = f", within {gap * 100:.2f}% of proven optimum" if gap is not None else ""
            return f"{base} (best found{pct}; not proven optimal)"
        if self.status is SolveStatus.HEURISTIC_INFEASIBLE:
            return "infeasible"
        if self.reference_value is not None:
            gap = self.reference_gap
            pct = f"{gap * 100:+.2f}%" if gap is not None else "n/a"
            return f"{base} (feasible; {pct} vs {self.reference_source})"
        return f"{base} (feasible)"
