/**
 * Waybill — Held-Karp Dynamic Programming Solver (§05, §08)
 * Solves TSP to exact global optimality in O(n^2 * 2^n) time.
 * Explicitly exposes the exponential "memory wall" as problem size n increases.
 */

import { DistanceMatrix, Instance, SolveReport, SolveStatus } from '../../types';
import { checkInstanceFeasibility } from '../eval/feasibility';

export interface HeldKarpOptions {
  timeoutMs?: number;
  maxMemoryMb?: number;
}

export function solveHeldKarp(instance: Instance, options: HeldKarpOptions = {}): SolveReport {
  const startTime = performance.now();
  const matrix = instance.distanceMatrix.matrix;
  const n = instance.stops.length;
  const timeoutMs = options.timeoutMs ?? 10000;
  const maxMemoryMb = options.maxMemoryMb ?? 512;

  // Theoretical state space: 2^n * n table entries
  const numStates = 1 << n;
  const estimatedMemoryMb = (numStates * n * 8) / (1024 * 1024);

  if (n > 23 || estimatedMemoryMb > maxMemoryMb) {
    // Memory wall reached!
    return {
      problem_type: 'TSP',
      status: SolveStatus.HEURISTIC_INFEASIBLE,
      permitted_wording: `Memory Wall Reached: n=${n} requires ~${estimatedMemoryMb.toFixed(1)} MB of DP table state (Limit: ${maxMemoryMb} MB).`,
      objective_value: 0,
      objective_units: instance.distanceMatrix.units,
      stop_reason: 'memory_cap',
      wall_time_ms: Math.round(performance.now() - startTime),
      cpu_time_ms: 0,
      peak_memory_mb: estimatedMemoryMb,
      routes: [],
      solver_config_hash: 'hk-dp-v1',
      distance_matrix_hash: instance.distanceMatrix.hash,
      hardware_id: typeof navigator !== 'undefined' ? `${navigator.hardwareConcurrency || 4}-core Client` : 'Node-Env',
      solver_name: 'Held–Karp Dynamic Programming',
      solver_tier: 'MANDATORY',
      feasibilityAudit: {
        passed: false,
        allCustomersVisitedOnce: false,
        capacityRespected: false,
        timeWindowsRespected: false,
        shiftDurationRespected: false,
        violations: [`Instance size n=${n} exceeds Held-Karp memory bound.`],
      },
    };
  }

  // dp[mask][u] = min cost to visit subset (mask) starting at 0 and ending at u
  // parent[mask][u] = predecessor node on optimal path
  const dp = new Float64Array(numStates * n).fill(Infinity);
  const parent = new Int16Array(numStates * n).fill(-1);

  // Base case: starting at depot (node 0) with subset {0} (mask = 1)
  dp[1 * n + 0] = 0;

  let stopReason: 'optimal' | 'timeout' = 'optimal';
  let statesComputed = 0;

  // Iterate over subset sizes s = 2 to n
  for (let size = 2; size <= n; size++) {
    if (performance.now() - startTime > timeoutMs) {
      stopReason = 'timeout';
      break;
    }

    // Generate subsets of size `size` containing node 0 (bit 0 = 1)
    for (let mask = 1; mask < numStates; mask += 2) {
      if (countBits(mask) !== size) continue;

      for (let v = 1; v < n; v++) {
        if ((mask & (1 << v)) === 0) continue; // v must be in mask

        const prevMask = mask ^ (1 << v);
        let minCost = Infinity;
        let bestPrev = -1;

        for (let u = 0; u < n; u++) {
          if ((prevMask & (1 << u)) === 0) continue; // u must be in prevMask

          const prevCost = dp[prevMask * n + u];
          if (prevCost === Infinity) continue;

          const edgeCost = matrix[u][v];
          const total = prevCost + edgeCost;

          if (total < minCost) {
            minCost = total;
            bestPrev = u;
          }
        }

        if (minCost < Infinity) {
          dp[mask * n + v] = minCost;
          parent[mask * n + v] = bestPrev;
          statesComputed++;
        }
      }
    }
  }

  const fullMask = (1 << n) - 1;
  let minTourCost = Infinity;
  let lastNode = -1;

  if (stopReason === 'optimal') {
    for (let u = 1; u < n; u++) {
      const pathCost = dp[fullMask * n + u];
      if (pathCost === Infinity) continue;
      const returnCost = matrix[u][0];
      const total = pathCost + returnCost;
      if (total < minTourCost) {
        minTourCost = total;
        lastNode = u;
      }
    }
  }

  // Reconstruct optimal path
  const bestTour: number[] = [];
  if (minTourCost < Infinity && lastNode !== -1) {
    let currNode = lastNode;
    let currMask = fullMask;

    while (currNode !== 0 && currNode !== -1) {
      bestTour.push(currNode);
      const prev = parent[currMask * n + currNode];
      currMask = currMask ^ (1 << currNode);
      currNode = prev;
    }
    bestTour.push(0);
    bestTour.reverse();
    bestTour.push(0); // return to depot
  }

  const wallTimeMs = Math.round(performance.now() - startTime);
  const rawRoute = [{ vehicleId: instance.vehicles[0].id, stopIds: bestTour.length > 0 ? bestTour : [0, 0] }];
  const feasibility = checkInstanceFeasibility(instance, rawRoute);

  const isProven = stopReason === 'optimal' && minTourCost < Infinity;

  return {
    problem_type: 'TSP',
    status: isProven ? SolveStatus.PROVEN_OPTIMAL_TSP : SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT,
    permitted_wording: isProven
      ? '"Optimal" — for this TSP instance only (Held-Karp DP Proof)'
      : 'Exact search timed out before completion.',
    objective_value: isProven ? minTourCost : 0,
    objective_units: instance.distanceMatrix.units,
    best_lower_bound: isProven ? minTourCost : undefined,
    proven_gap: isProven ? 0 : undefined,
    stop_reason: stopReason,
    wall_time_ms: wallTimeMs,
    cpu_time_ms: wallTimeMs,
    peak_memory_mb: parseFloat(estimatedMemoryMb.toFixed(2)),
    nodes_explored: statesComputed,
    nodes_created: numStates * n,
    routes: feasibility.auditedRoutes,
    solver_config_hash: 'hk-dp-v1',
    distance_matrix_hash: instance.distanceMatrix.hash,
    hardware_id: typeof navigator !== 'undefined' ? `${navigator.hardwareConcurrency || 4}-core Client` : 'Node-Env',
    solver_name: 'Held–Karp Dynamic Programming',
    solver_tier: 'MANDATORY',
    certificate: isProven ? {
      proofType: 'DYNAMIC_PROGRAMMING_MEMOIZATION',
      nodesVerified: statesComputed,
      optimalTour: bestTour,
      boundTightness: 1.0,
      verifiedAt: new Date().toISOString(),
    } : undefined,
    feasibilityAudit: {
      passed: feasibility.passed,
      allCustomersVisitedOnce: feasibility.allCustomersVisitedOnce,
      capacityRespected: feasibility.capacityRespected,
      timeWindowsRespected: feasibility.timeWindowsRespected,
      shiftDurationRespected: feasibility.shiftDurationRespected,
      violations: feasibility.violations,
    },
  };
}

function countBits(n: number): number {
  let count = 0;
  while (n > 0) {
    count += n & 1;
    n >>= 1;
  }
  return count;
}
