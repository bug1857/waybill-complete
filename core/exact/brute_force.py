"""Exhaustive enumeration.

The root of the validation chain. Every other exact solver is checked against
this one on instances small enough for it to finish, so it is written for
obvious correctness rather than for speed.

Two symmetry reductions are applied, and both must preserve exhaustiveness:

* **Fixing the depot as the tour's start** is safe. Every cyclic tour has
  exactly one rotation beginning at the depot, so fixing it loses nothing.

* **Skipping reversed duplicates** is safe only on a symmetric matrix, where a
  tour and its reverse cost the same. It is implemented by discarding any
  customer permutation whose first element exceeds its last, which keeps exactly
  one of each reverse pair.

  Note what is *not* safe: fixing a particular customer to be visited first.
  That excludes genuine tours rather than duplicates -- with customers A, B, C it
  enumerates only 2 of the 3 distinct tours and can miss the optimum outright.
  The distinction matters because both reductions look superficially alike.
"""

import time
from itertools import permutations

from core.model.instance import Instance, ProblemType
from core.model.solution import Solution
from core.reporting.report import SolveReport
from core.reporting.status import SolveStatus, StopReason
from core.solver import UNLIMITED, Budget

#: Refuse instances above this size. 10 customers is already ~1.8M tours after
#: halving; the guard makes a misconfigured sweep fail loudly instead of hanging.
MAX_SUPPORTED_CUSTOMERS: int = 10


class BruteForceSolver:
    """Enumerates every distinct tour and returns the cheapest."""

    def __init__(self, max_customers: int = MAX_SUPPORTED_CUSTOMERS) -> None:
        self._max_customers = max_customers

    @property
    def name(self) -> str:
        return "brute_force"

    def solve(
        self, instance: Instance, budget: Budget = UNLIMITED
    ) -> tuple[Solution, SolveReport]:
        if instance.problem_type is not ProblemType.TSP:
            raise ValueError(
                f"brute force solves TSP only; instance '{instance.name}' is "
                f"{instance.problem_type.value}"
            )

        customers = instance.customer_indices
        if len(customers) > self._max_customers:
            raise ValueError(
                f"instance '{instance.name}' has {len(customers)} customers, above "
                f"the brute-force limit of {self._max_customers}. This solver is "
                f"ground truth for small instances, not a general method."
            )

        matrix = instance.matrix
        depot = instance.depot_index
        # Only valid when reversing a tour preserves its cost.
        skip_reversals = matrix.is_symmetric and len(customers) > 2

        best_sequence: tuple[int, ...] = ()
        best_cost = -1
        explored = 0

        start = time.perf_counter()
        cpu_start = time.process_time()

        if not customers:
            best_cost = 0
        else:
            for perm in permutations(customers):
                if skip_reversals and perm[0] > perm[-1]:
                    continue
                explored += 1
                cost = matrix.cost(depot, perm[0])
                for a, b in zip(perm, perm[1:]):
                    cost += matrix.cost(a, b)
                cost += matrix.cost(perm[-1], depot)
                if best_cost < 0 or cost < best_cost:
                    best_cost, best_sequence = cost, perm

        wall_ms = (time.perf_counter() - start) * 1000.0
        cpu_ms = (time.process_time() - cpu_start) * 1000.0

        solution = Solution.single_tour(
            best_sequence, vehicle_id=instance.vehicles[0].id
        )
        report = SolveReport(
            solver_name=self.name,
            problem_type=ProblemType.TSP,
            status=SolveStatus.PROVEN_OPTIMAL_TSP,
            stop_reason=StopReason.OPTIMAL,
            objective_value=best_cost,
            objective_units=matrix.unit,
            best_lower_bound=best_cost,
            wall_time_ms=wall_ms,
            cpu_time_ms=cpu_ms,
            nodes_explored=explored,
            nodes_created=explored,
            distance_matrix_hash=matrix.content_hash,
            solver_config_hash=budget.config_hash(),
        )
        return solution, report
