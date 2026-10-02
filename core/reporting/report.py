"""The SolveReport contract.

Every solver returns one of these. The validation in ``__post_init__`` is the
claim discipline made mechanical: a report that claims proven optimality without
a proof condition, or supplies a reference value with no provenance, cannot be
constructed at all.

The benchmark harness refuses to plot a run whose mandatory fields are missing,
so a figure in the report always traces back to a complete record.
"""

import math
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
        if not isinstance(self.solver_name, str) or not self.solver_name.strip():
            raise ValueError("solver_name must be non-empty")
        if not isinstance(self.problem_type, ProblemType):
            raise TypeError("problem_type must be a ProblemType")
        if not isinstance(self.status, SolveStatus):
            raise TypeError("status must be a SolveStatus")
        if not isinstance(self.stop_reason, StopReason):
            raise TypeError("stop_reason must be a StopReason")
        if not isinstance(self.objective_units, Unit):
            raise TypeError("objective_units must be a Unit")
        _require_int("objective_value", self.objective_value)
        if self.objective_value < 0:
            raise ValueError("objective_value must be non-negative")

        for name in ("best_lower_bound", "reference_value"):
            value = getattr(self, name)
            if value is not None:
                _require_int(name, value)
                if value < 0:
                    raise ValueError(f"{name} must be non-negative")
        if (
            self.best_lower_bound is not None
            and self.best_lower_bound > self.objective_value
        ):
            raise ValueError(
                f"lower bound {self.best_lower_bound} exceeds objective "
                f"{self.objective_value}: the bound is invalid, and an invalid "
                f"bound may already have pruned the optimum"
            )

        for name in (
            "nodes_created",
            "nodes_explored",
            "nodes_pruned",
            "peak_frontier",
        ):
            value = getattr(self, name)
            _require_int(name, value)
            if value < 0:
                raise ValueError(f"{name} must be non-negative")

        if self.seed is not None:
            _require_int("seed", self.seed)

        for name in ("wall_time_ms", "cpu_time_ms", "bound_time_ms"):
            value = getattr(self, name)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError(f"{name} must be a finite non-negative number")
        if self.peak_memory_mb is not None and (
            not isinstance(self.peak_memory_mb, (int, float))
            or isinstance(self.peak_memory_mb, bool)
            or not math.isfinite(self.peak_memory_mb)
            or self.peak_memory_mb < 0
        ):
            raise ValueError("peak_memory_mb must be a finite non-negative number")

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
            if self.best_lower_bound != self.objective_value:
                raise ValueError(
                    f"{self.status.value} requires best_lower_bound to equal "
                    "objective_value"
                )
        elif self.stop_reason is StopReason.OPTIMAL:
            raise ValueError(
                "stop_reason=OPTIMAL requires status=PROVEN_OPTIMAL_TSP"
            )

        if self.status is SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT:
            if self.stop_reason not in {
                StopReason.TIMEOUT,
                StopReason.NODE_CAP,
                StopReason.MEMORY_CAP,
                StopReason.CANCELLED,
            }:
                raise ValueError(
                    "EXACT_TIMEOUT_WITH_INCUMBENT requires an interruption "
                    "stop reason"
                )
            if self.best_lower_bound is None:
                raise ValueError(
                    "EXACT_TIMEOUT_WITH_INCUMBENT must carry best_lower_bound, "
                    "otherwise the residual gap is unknown and the run is unusable"
                )
            if self.best_lower_bound == self.objective_value:
                raise ValueError(
                    "an incumbent equal to its lower bound is proven; use "
                    "PROVEN_OPTIMAL_TSP instead of an interruption status"
                )

        if self.status is SolveStatus.HEURISTIC_FEASIBLE_CVRPTW:
            if self.problem_type is not ProblemType.CVRPTW:
                raise ValueError(
                    "HEURISTIC_FEASIBLE_CVRPTW is only valid for CVRPTW"
                )
            if self.stop_reason is StopReason.INFEASIBLE:
                raise ValueError(
                    "a feasible status cannot use stop_reason=INFEASIBLE"
                )

        if self.status is SolveStatus.HEURISTIC_FEASIBLE_TSP:
            if self.problem_type is not ProblemType.TSP:
                raise ValueError("HEURISTIC_FEASIBLE_TSP is only valid for TSP")
            if self.stop_reason is StopReason.INFEASIBLE:
                raise ValueError(
                    "a feasible status cannot use stop_reason=INFEASIBLE"
                )

        if self.status is SolveStatus.HEURISTIC_INFEASIBLE:
            if self.stop_reason is not StopReason.INFEASIBLE:
                raise ValueError(
                    "HEURISTIC_INFEASIBLE requires stop_reason=INFEASIBLE"
                )
        elif self.stop_reason is StopReason.INFEASIBLE:
            raise ValueError(
                "stop_reason=INFEASIBLE requires status=HEURISTIC_INFEASIBLE"
            )

        if self.status is SolveStatus.HEURISTIC_PARTIAL and self.stop_reason not in {
            StopReason.TIMEOUT,
            StopReason.NODE_CAP,
            StopReason.MEMORY_CAP,
            StopReason.CANCELLED,
        }:
            raise ValueError(
                "HEURISTIC_PARTIAL requires an interruption stop reason"
            )

        if self.reference_value is not None and self.reference_source is None:
            raise ValueError(
                "reference_value requires reference_source: an unattributed "
                "comparator cannot be checked by anyone"
            )
        if self.reference_source is not None and self.reference_value is None:
            raise ValueError(
                "reference_source requires reference_value"
            )
        if self.reference_source is not None:
            if (
                not isinstance(self.reference_source, str)
                or not self.reference_source.strip()
            ):
                raise ValueError("reference_source must be a non-empty string")
        if not self.status.is_feasible and self.reference_value is not None:
            raise ValueError(
                "infeasible or partial candidates cannot carry a reference gap"
            )
        if (
            self.status is SolveStatus.REFERENCE_GAP_ONLY
            and self.reference_value is None
        ):
            raise ValueError(
                "REFERENCE_GAP_ONLY requires a named reference value"
            )

    @property
    def proven_gap(self) -> float | None:
        """Incumbent-relative primal/dual gap, or ``None`` without a bound.

        This is ``(incumbent - lower_bound) / incumbent``. It measures the open
        interval between two valid bounds relative to the incumbent; it must not
        be worded as "within X% of optimum", whose denominator would be the
        unknown optimum.
        """
        if self.best_lower_bound is None:
            return None
        if self.objective_value == 0:
            return 0.0
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
            pct = (
                f"; {gap * 100:.2f}% incumbent-relative gap to lower bound"
                if gap is not None
                else ""
            )
            return f"{base} (best found{pct}; not proven optimal)"
        if self.status is SolveStatus.HEURISTIC_FEASIBLE_TSP:
            return f"{base} (feasible TSP tour; not proven optimal)"
        if self.status is SolveStatus.HEURISTIC_PARTIAL:
            return f"{base} (partial incumbent; not a complete feasible solution)"
        if self.status is SolveStatus.HEURISTIC_INFEASIBLE:
            return "candidate infeasible (not proof that the instance is infeasible)"
        if self.reference_value is not None:
            gap = self.reference_gap
            pct = f"{gap * 100:+.2f}%" if gap is not None else "n/a"
            return f"{base} (feasible; {pct} vs {self.reference_source})"
        return f"{base} (feasible)"


def _require_int(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
