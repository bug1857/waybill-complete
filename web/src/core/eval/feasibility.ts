/**
 * Waybill — Independent Feasibility Gate & Evaluator (§02, §08, §10)
 * Evaluates visit-once, vehicle capacity, hard time windows, service times, and shift limits.
 * All arithmetic uses integer seconds and integer metres.
 */

import { DistanceMatrix, Instance, Route, RouteStopAudit, SolveReport, SolveStatus, Stop } from '../../types';

export interface FeasibilityResult {
  passed: boolean;
  allCustomersVisitedOnce: boolean;
  capacityRespected: boolean;
  timeWindowsRespected: boolean;
  shiftDurationRespected: boolean;
  violations: string[];
  totalDistanceMetres: number;
  totalDurationSec: number;
  auditedRoutes: Route[];
}

/**
 * Assumes average courier urban driving speed: 25 km/h ≈ 6.94 m/s (or 1 meter = 0.144 sec)
 */
export function travelTimeFromDistance(distMetres: number): number {
  const speedMetersPerSec = 7.0; // ~25.2 km/h
  return Math.round(distMetres / speedMetersPerSec);
}

/**
 * Audit a single route for a specific vehicle
 */
export function auditSingleRoute(
  stopIds: number[],
  vehicleId: number,
  stopsMap: Map<number, Stop>,
  matrix: number[][],
  maxCapacity: number,
  maxShiftSec: number,
  startTimeSec = 28800 // default 08:00 AM (28800 sec)
): { route: Route; violations: string[] } {
  const violations: string[] = [];
  const audits: RouteStopAudit[] = [];

  let currentSec = startTimeSec;
  let cumulativeLoad = 0;
  let totalDistanceMetres = 0;
  let totalDemand = 0;

  if (stopIds.length < 2) {
    return {
      route: {
        vehicleId,
        stopIds,
        distanceMetres: 0,
        durationSec: 0,
        totalDemand: 0,
        feasible: true,
        violations: [],
        stopAudits: [],
      },
      violations: [],
    };
  }

  for (let idx = 0; idx < stopIds.length; idx++) {
    const stopId = stopIds[idx];
    const stop = stopsMap.get(stopId);

    if (!stop) {
      violations.push(`Unknown stop ID ${stopId} in route for vehicle ${vehicleId}`);
      continue;
    }

    let distFromPrev = 0;
    let travelTime = 0;

    if (idx > 0) {
      const prevStopId = stopIds[idx - 1];
      distFromPrev = matrix[prevStopId]?.[stopId] ?? 0;
      travelTime = travelTimeFromDistance(distFromPrev);
      currentSec += travelTime;
      totalDistanceMetres += distFromPrev;
    }

    const arrivalSec = currentSec;
    let waitingSec = 0;
    let windowViolation = false;

    // Check time window
    if (stop.window) {
      if (arrivalSec < stop.window.startSec) {
        waitingSec = stop.window.startSec - arrivalSec;
        currentSec = stop.window.startSec; // Wait until window opens
      } else if (arrivalSec > stop.window.endSec) {
        windowViolation = true;
        const minsLate = Math.round((arrivalSec - stop.window.endSec) / 60);
        violations.push(
          `Vehicle ${vehicleId}: Stop #${stop.id} (${stop.name}) arrived late by ${minsLate} min (Arrival: ${formatSeconds(arrivalSec)}, Window End: ${formatSeconds(stop.window.endSec)})`
        );
      }
    }

    const serviceStartSec = currentSec;
    const serviceDuration = stop.isDepot ? 0 : stop.serviceTimeSec;
    currentSec += serviceDuration;
    const departureSec = currentSec;

    // Capacity tracking
    if (!stop.isDepot) {
      cumulativeLoad += stop.demand;
      totalDemand += stop.demand;
    }

    let capacityViolation = false;
    if (cumulativeLoad > maxCapacity) {
      capacityViolation = true;
      violations.push(
        `Vehicle ${vehicleId}: Capacity exceeded at Stop #${stop.id} (Load: ${cumulativeLoad} / Max: ${maxCapacity})`
      );
    }

    audits.push({
      stopId: stop.id,
      name: stop.name,
      demand: stop.demand,
      cumulativeLoad,
      distanceFromPrevMetres: distFromPrev,
      travelTimeSec: travelTime,
      arrivalSec,
      serviceStartSec,
      departureSec,
      waitingSec,
      windowViolation,
      capacityViolation,
    });
  }

  const routeDurationSec = currentSec - startTimeSec;
  if (routeDurationSec > maxShiftSec) {
    const hoursOver = ((routeDurationSec - maxShiftSec) / 3600).toFixed(2);
    violations.push(
      `Vehicle ${vehicleId}: Max shift exceeded by ${hoursOver}h (Duration: ${formatSeconds(routeDurationSec)}, Limit: ${formatSeconds(maxShiftSec)})`
    );
  }

  const isFeasible = violations.length === 0;

  return {
    route: {
      vehicleId,
      stopIds,
      distanceMetres: totalDistanceMetres,
      durationSec: routeDurationSec,
      totalDemand,
      feasible: isFeasible,
      violations,
      stopAudits: audits,
    },
    violations,
  };
}

/**
 * Complete Independent Feasibility Checker for the whole instance
 */
export function checkInstanceFeasibility(
  instance: Instance,
  routes: { vehicleId: number; stopIds: number[] }[]
): FeasibilityResult {
  const stopsMap = new Map<number, Stop>();
  instance.stops.forEach((s) => stopsMap.set(s.id, s));

  const matrix = instance.distanceMatrix.matrix;
  const violations: string[] = [];
  const visitedCustomerCounts = new Map<number, number>();

  // Initialize non-depot customers count
  instance.stops.forEach((s) => {
    if (!s.isDepot && s.id !== instance.depot.id) {
      visitedCustomerCounts.set(s.id, 0);
    }
  });

  const vehiclesMap = new Map<number, number>();
  instance.vehicles.forEach((v) => vehiclesMap.set(v.id, v.capacity));

  let totalDistanceMetres = 0;
  let totalDurationSec = 0;
  const auditedRoutes: Route[] = [];

  for (const rawRoute of routes) {
    const vehicle = instance.vehicles.find((v) => v.id === rawRoute.vehicleId) || instance.vehicles[0];
    const { route, violations: routeViolations } = auditSingleRoute(
      rawRoute.stopIds,
      vehicle.id,
      stopsMap,
      matrix,
      vehicle.capacity,
      vehicle.maxShiftSec
    );

    auditedRoutes.push(route);
    violations.push(...routeViolations);
    totalDistanceMetres += route.distanceMetres;
    totalDurationSec += route.durationSec;

    // Track customer visits
    for (let i = 1; i < rawRoute.stopIds.length - 1; i++) {
      const stopId = rawRoute.stopIds[i];
      if (visitedCustomerCounts.has(stopId)) {
        visitedCustomerCounts.set(stopId, (visitedCustomerCounts.get(stopId) || 0) + 1);
      }
    }
  }

  // Check Visit-Once Constraint
  let allCustomersVisitedOnce = true;
  visitedCustomerCounts.forEach((count, stopId) => {
    if (count === 0) {
      violations.push(`Unserved Stop: #${stopId} (${stopsMap.get(stopId)?.name}) was never visited.`);
      allCustomersVisitedOnce = false;
    } else if (count > 1) {
      violations.push(`Duplicate Visit: Stop #${stopId} was visited ${count} times.`);
      allCustomersVisitedOnce = false;
    }
  });

  const capacityRespected = !violations.some((v) => v.includes('Capacity exceeded'));
  const timeWindowsRespected = !violations.some((v) => v.includes('arrived late'));
  const shiftDurationRespected = !violations.some((v) => v.includes('Max shift exceeded'));

  const passed = violations.length === 0 && allCustomersVisitedOnce;

  return {
    passed,
    allCustomersVisitedOnce,
    capacityRespected,
    timeWindowsRespected,
    shiftDurationRespected,
    violations,
    totalDistanceMetres,
    totalDurationSec,
    auditedRoutes,
  };
}

/**
 * Compute the exact tour length for a single TSP cycle: 0 -> ... -> 0
 */
export function calculateTourCost(tour: number[], matrix: number[][]): number {
  if (tour.length < 2) return 0;
  let cost = 0;
  for (let i = 0; i < tour.length - 1; i++) {
    cost += matrix[tour[i]][tour[i + 1]];
  }
  // Return to start if not closed
  if (tour[tour.length - 1] !== tour[0]) {
    cost += matrix[tour[tour.length - 1]][tour[0]];
  }
  return cost;
}

export function formatSeconds(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}${s > 0 ? `:${s.toString().padStart(2, '0')}` : ''}`;
}
