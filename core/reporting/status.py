"""Solution status.

Exactness is a property of one formulation, one instance, and one solver run --
never of the application. These statuses exist so that a proven-optimal 12-stop
TSP tour and a heuristic 150-stop fleet plan cannot be described with the same
word, and so that the constraint is checked by the type system rather than
remembered by whoever writes the report.
"""

from enum import StrEnum


class SolveStatus(StrEnum):
    #: An exact solver finished with a valid proof condition on a single-vehicle
    #: instance. "Optimal" is permitted, for that TSP instance only.
    PROVEN_OPTIMAL_TSP = "PROVEN_OPTIMAL_TSP"

    #: Exact search found a feasible incumbent but was interrupted before proving
    #: optimality. Report the incumbent *and* the best valid lower bound.
    #:
    #: The historical name is retained for API compatibility; ``stop_reason``
    #: distinguishes wall time, node, memory, and cancellation interruptions.
    EXACT_TIMEOUT_WITH_INCUMBENT = "EXACT_TIMEOUT_WITH_INCUMBENT"

    #: A TSP tour passed feasibility checks but carries no optimality proof.
    #: Used by constructive heuristics and local search.
    HEURISTIC_FEASIBLE_TSP = "HEURISTIC_FEASIBLE_TSP"

    #: A multi-vehicle plan passed the independent feasibility gate. Quality is
    #: only ever relative to a named comparator.
    HEURISTIC_FEASIBLE_CVRPTW = "HEURISTIC_FEASIBLE_CVRPTW"

    #: Candidate violates capacity, window, shift, or visit-once constraints.
    HEURISTIC_INFEASIBLE = "HEURISTIC_INFEASIBLE"

    #: A heuristic was interrupted with only a partial incumbent. This is not a
    #: complete feasible plan and is not evidence that the instance is infeasible.
    HEURISTIC_PARTIAL = "HEURISTIC_PARTIAL"

    #: Compared against OR-Tools or a best-known value, not a proven optimum.
    REFERENCE_GAP_ONLY = "REFERENCE_GAP_ONLY"

    @property
    def permits_word_optimal(self) -> bool:
        """Whether a report with this status may use the word "optimal"."""
        return self is SolveStatus.PROVEN_OPTIMAL_TSP

    @property
    def is_feasible(self) -> bool:
        return self not in {
            SolveStatus.HEURISTIC_INFEASIBLE,
            SolveStatus.HEURISTIC_PARTIAL,
        }

    @property
    def permitted_wording(self) -> str:
        """The strongest phrase this status entitles a report to use."""
        return {
            SolveStatus.PROVEN_OPTIMAL_TSP: "optimal for this TSP instance",
            SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT: "best found, with a valid lower bound",
            SolveStatus.HEURISTIC_FEASIBLE_TSP: "feasible TSP tour, not proven optimal",
            SolveStatus.HEURISTIC_FEASIBLE_CVRPTW: "feasible",
            SolveStatus.HEURISTIC_INFEASIBLE: "candidate infeasible; not an infeasibility proof",
            SolveStatus.HEURISTIC_PARTIAL: "partial incumbent; not a complete feasible solution",
            SolveStatus.REFERENCE_GAP_ONLY: "compared to a reference, not a proven optimum",
        }[self]


class StopReason(StrEnum):
    """Why a solver stopped. Essential for fair exact-vs-heuristic comparison:
    a run that hit a timeout is a data point about the budget, not about quality.
    """

    OPTIMAL = "optimal"
    TIMEOUT = "timeout"
    NODE_CAP = "node_cap"
    MEMORY_CAP = "memory_cap"
    INFEASIBLE = "infeasible"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
