/**
 * Waybill — Core Types and Contracts
 * Adheres strictly to the SolveReport contract, Status Enum, and Claim Model (§02, §06, §07)
 */

export type ProblemType = 'TSP' | 'CVRP' | 'CVRPTW';

export enum SolveStatus {
  PROVEN_OPTIMAL_TSP = 'PROVEN_OPTIMAL_TSP',
  EXACT_TIMEOUT_WITH_INCUMBENT = 'EXACT_TIMEOUT_WITH_INCUMBENT',
  HEURISTIC_FEASIBLE_CVRPTW = 'HEURISTIC_FEASIBLE_CVRPTW',
  HEURISTIC_INFEASIBLE = 'HEURISTIC_INFEASIBLE',
  REFERENCE_GAP_ONLY = 'REFERENCE_GAP_ONLY',
}

export type StopReason = 'optimal' | 'timeout' | 'memory_cap' | 'infeasible' | 'cancelled' | 'max_iterations';

export interface TimeWindow {
  startSec: number; // e.g. 32400 (09:00)
  endSec: number;   // e.g. 39600 (11:00)
}

export interface Stop {
  id: number;
  name: string;
  x: number; // coordinates for display / Euclidean
  y: number;
  lat?: number; // Real GPS coordinates for road map
  lng?: number;
  demand: number; // parcel count (discrete integer)
  window?: TimeWindow;
  serviceTimeSec: number; // e.g. 300 (5 mins at door)
  isDepot?: boolean;
}

export interface Vehicle {
  id: number;
  name: string;
  capacity: number; // max parcel count
  maxShiftSec: number; // shift duration limit e.g. 28800 (8 hours)
  depotId: number;
  color: string;
}

export interface DistanceMatrix {
  matrix: number[][]; // cost in metres or seconds (integer)
  isSymmetric: boolean;
  hash: string;
  units: 'metres' | 'seconds' | 'tsplib_units';
  provider: 'EUCLIDEAN_2D' | 'HAVERSINE' | 'SYNTHETIC_ASYMMETRIC' | 'OSRM_ROAD_ASYMMETRIC' | 'TSPLIB_EXACT';
}

export interface Instance {
  id: string;
  name: string;
  type: ProblemType;
  stops: Stop[];
  vehicles: Vehicle[];
  depot: Stop;
  distanceMatrix: DistanceMatrix;
  description?: string;
  knownOptimum?: number;
  source?: string;
}

export interface RouteStopAudit {
  stopId: number;
  name: string;
  demand: number;
  cumulativeLoad: number;
  distanceFromPrevMetres: number;
  travelTimeSec: number;
  arrivalSec: number;
  serviceStartSec: number;
  departureSec: number;
  waitingSec: number;
  windowViolation: boolean;
  capacityViolation: boolean;
}

export interface Route {
  vehicleId: number;
  stopIds: number[]; // sequence of stop IDs starting and ending at depot
  distanceMetres: number;
  durationSec: number;
  totalDemand: number;
  feasible: boolean;
  violations: string[];
  stopAudits: RouteStopAudit[];
}

export interface SolveTracePoint {
  iteration: number;
  cost: number;
  timeMs: number;
  temperature?: number;
  lowerBound?: number;
  bestCost?: number;
  action?: string;
}

export interface BranchBoundNodeInfo {
  id: number;
  parentId?: number;
  depth: number;
  partialTour: number[];
  lowerBound: number;
  pruned: boolean;
  reason?: 'pruned_by_bound' | 'infeasible' | 'solution_found' | 'branched';
}

export interface SolveCertificate {
  proofType: 'EXHAUSTIVE_ENUMERATION' | 'BRANCH_AND_BOUND_EXHAUSTION' | 'DYNAMIC_PROGRAMMING_MEMOIZATION';
  nodesVerified: number;
  optimalTour: number[];
  boundTightness: number;
  verifiedAt: string;
}

export interface SolveReport {
  problem_type: ProblemType;
  status: SolveStatus;
  permitted_wording: string; // e.g. "Optimal" or "Feasible" or "Gap to reference"
  objective_value: number;
  objective_units: 'metres' | 'seconds' | 'tsplib_units';
  best_lower_bound?: number;
  proven_gap?: number; // (incumbent - lower_bound)/incumbent — only when valid
  reference_value?: number;
  reference_source?: string;
  reference_gap?: number; // (incumbent - reference_value)/reference_value
  stop_reason: StopReason;
  wall_time_ms: number;
  cpu_time_ms: number;
  peak_memory_mb: number;
  nodes_created?: number;
  nodes_explored?: number;
  nodes_pruned?: number;
  peak_frontier?: number;
  bound_time_ms?: number;
  search_time_ms?: number;
  routes: Route[];
  seed?: number;
  solver_config_hash: string;
  distance_matrix_hash: string;
  hardware_id: string;
  solver_name: string;
  solver_tier: 'MANDATORY' | 'RECOMMENDED' | 'REFERENCE';
  trace?: SolveTracePoint[];
  bbTree?: BranchBoundNodeInfo[];
  certificate?: SolveCertificate;
  feasibilityAudit: {
    passed: boolean;
    allCustomersVisitedOnce: boolean;
    capacityRespected: boolean;
    timeWindowsRespected: boolean;
    shiftDurationRespected: boolean;
    violations: string[];
  };
}

export interface BenchmarkSweepPoint {
  n: number;
  solverName: string;
  wallTimeMs: number;
  objectiveValue: number;
  status: SolveStatus;
  nodesExplored?: number;
  nodesPruned?: number;
  peakFrontier?: number;
  boundTimeMs?: number;
  lowerBound?: number;
  gapPercent?: number;
  peakMemoryMb: number;
  solvedFraction?: number;
}
