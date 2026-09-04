"""Held-Karp dynamic programming.

The classical exact TSP algorithm. ``dp[mask][j]`` is the cheapest path that
starts at the depot, visits exactly the customers in ``mask``, and ends at ``j``.
Each state extends by one customer, so the recurrence is::

    dp[mask | 1<<k][k] = min over j in mask of dp[mask][j] + d(j, k)

Complexity is O(n^2 * 2^n) time and O(n * 2^n) memory. **It dies on memory, not
time**, which is worth stating precisely because it is the more interesting
result: the table has 2^(n-1) * (n-1) entries, so each additional stop roughly
doubles the requirement. Locating that wall on real hardware is one of the
project's headline measurements, so this implementation refuses to start rather
than exhausting the machine, and reports the refusal as data.
"""

import time

from core.model.instance import Instance, ProblemType
from core.model.solution import Solution
from core.reporting.report import SolveReport
from core.reporting.status import SolveStatus, StopReason
from core.solver import UNLIMITED, Budget

#: Bytes per table entry, measured against CPython's list-of-int representation
#: (8-byte pointer plus a small int object). Deliberately conservative.
BYTES_PER_ENTRY = 40

#: Refuse above this unless explicitly raised. 2^19 * 19 entries is already
#: several hundred megabytes in CPython.
DEFAULT_MAX_CUSTOMERS = 19


class HeldKarpSolver:
    """Exact TSP by dynamic programming over subsets."""

    def __init__(self, max_customers: int = DEFAULT_MAX_CUSTOMERS) -> None:
        self._max_customers = max_customers

    @property
    def name(self) -> str:
        return "held_karp"

    def estimated_memory_mb(self, n_customers: int) -> float:
        """Table size for ``n_customers``, in megabytes."""
        if n_customers <= 0:
            return 0.0
        entries = (1 << n_customers) * n_customers
        return entries * BYTES_PER_ENTRY / (1024 * 1024)

    def solve(
        self, instance: Instance, budget: Budget = UNLIMITED
    ) -> tuple[Solution, SolveReport]:
        if instance.problem_type is not ProblemType.TSP:
            raise ValueError(
                f"Held-Karp solves TSP only; '{instance.name}' is "
                f"{instance.problem_type.value}"
            )

        matrix = instance.matrix
        depot = instance.depot_index
        customers = list(instance.customer_indices)
        m = len(customers)

        if m > self._max_customers:
            raise ValueError(
                f"'{instance.name}' has {m} customers; the Held-Karp table would "
                f"need about {self.estimated_memory_mb(m):.0f} MB. The limit is "
                f"{self._max_customers} customers "
                f"(~{self.estimated_memory_mb(self._max_customers):.0f} MB). "
                f"This wall is a result to report, not an error to work around."
            )

        start_wall = time.perf_counter()
        start_cpu = time.process_time()

        if m == 0:
            solution = Solution.single_tour((), vehicle_id=instance.vehicles[0].id)
            return solution, self._report(
                instance, 0, 0.0, 0.0, 0, budget
            )

        full = (1 << m) - 1
        INF = float("inf")
        # Flat tables indexed by mask * m + j.
        dp = [INF] * ((1 << m) * m)
        parent = [-1] * ((1 << m) * m)

        for j in range(m):
            dp[(1 << j) * m + j] = matrix.cost(depot, customers[j])

        states = 0
        for mask in range(1 << m):
            base = mask * m
            for j in range(m):
                if not mask & (1 << j):
                    continue
                cur = dp[base + j]
                if cur == INF:
                    continue
                states += 1
                cj = customers[j]
                for k in range(m):
                    if mask & (1 << k):
                        continue
                    nxt = mask | (1 << k)
                    cand = cur + matrix.cost(cj, customers[k])
                    idx = nxt * m + k
                    if cand < dp[idx]:
                        dp[idx] = cand
                        parent[idx] = j

        best_cost = INF
        best_last = -1
        for j in range(m):
            total = dp[full * m + j] + matrix.cost(customers[j], depot)
            if total < best_cost:
                best_cost, best_last = total, j

        # Walk the parent pointers back to reconstruct the tour.
        sequence: list[int] = []
        mask, j = full, best_last
        while j != -1:
            sequence.append(customers[j])
            pj = parent[mask * m + j]
            mask ^= 1 << j
            j = pj
        sequence.reverse()

        wall_ms = (time.perf_counter() - start_wall) * 1000.0
        cpu_ms = (time.process_time() - start_cpu) * 1000.0

        solution = Solution.single_tour(
            tuple(sequence), vehicle_id=instance.vehicles[0].id
        )
        return solution, self._report(
            instance, int(best_cost), wall_ms, cpu_ms, states, budget
        )

    def _report(
        self,
        instance: Instance,
        cost: int,
        wall_ms: float,
        cpu_ms: float,
        states: int,
        budget: Budget,
    ) -> SolveReport:
        m = len(instance.customer_indices)
        return SolveReport(
            solver_name=self.name,
            problem_type=ProblemType.TSP,
            status=SolveStatus.PROVEN_OPTIMAL_TSP,
            stop_reason=StopReason.OPTIMAL,
            objective_value=cost,
            objective_units=instance.matrix.unit,
            best_lower_bound=cost,
            wall_time_ms=wall_ms,
            cpu_time_ms=cpu_ms,
            peak_memory_mb=self.estimated_memory_mb(m),
            nodes_explored=states,
            nodes_created=(1 << m) * m if m else 0,
            distance_matrix_hash=instance.matrix.content_hash,
            solver_config_hash=budget.config_hash(),
        )
