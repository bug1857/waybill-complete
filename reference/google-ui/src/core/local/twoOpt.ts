/**
 * Waybill — 2-Opt with Strict Symmetry Guard (§05, §07)
 * Implements the textbook 2-opt move (segment reversal) with an explicit isSymmetric guard.
 * Exposes the Asymmetry Trap where naive 4-term O(1) evaluation silently optimizes the wrong objective.
 */

import { calculateTourCost } from '../eval/feasibility';

export interface TwoOptResult {
  tour: number[];
  cost: number;
  movesAccepted: number;
  symmetryGuardTriggered: boolean;
  evaluationComplexity: 'O(1) Textbook' | 'O(k) Honest Asymmetric';
  asymmetryDiscrepanciesDetected: number;
}

/**
 * 2-Opt local search with symmetry guard
 */
export function improveTwoOpt(
  tour: number[],
  matrix: number[][],
  isSymmetric: boolean,
  forceNaive = false,
  maxIterations = 500
): TwoOptResult {
  let currentTour = [...tour];
  if (currentTour.length < 5) {
    return {
      tour: currentTour,
      cost: calculateTourCost(currentTour, matrix),
      movesAccepted: 0,
      symmetryGuardTriggered: !isSymmetric,
      evaluationComplexity: isSymmetric ? 'O(1) Textbook' : 'O(k) Honest Asymmetric',
      asymmetryDiscrepanciesDetected: 0,
    };
  }

  let improved = true;
  let movesAccepted = 0;
  let iterations = 0;
  let discrepancies = 0;
  const n = currentTour.length - 1;

  while (improved && iterations < maxIterations) {
    improved = false;
    iterations++;

    for (let i = 0; i < n - 1; i++) {
      for (let j = i + 2; j < n; j++) {
        if (i === 0 && j === n - 1) continue; // Skip whole tour reversal

        const a = currentTour[i];
        const b = currentTour[i + 1];
        const c = currentTour[j];
        const d = currentTour[j + 1];

        // Textbook 4-term delta
        const textbookDelta = matrix[a][c] + matrix[b][d] - matrix[a][b] - matrix[c][d];

        let actualDelta = textbookDelta;

        if (!isSymmetric && !forceNaive) {
          // On asymmetric matrices, reversing segment [i+1 .. j] changes all internal edge costs!
          let internalReversalCostDelta = 0;
          for (let p = i + 1; p < j; p++) {
            const u = currentTour[p];
            const v = currentTour[p + 1];
            // Old forward edge: u -> v. New reversed edge: v -> u.
            internalReversalCostDelta += matrix[v][u] - matrix[u][v];
          }
          actualDelta = textbookDelta + internalReversalCostDelta;

          if (Math.abs(textbookDelta - actualDelta) > 0.001) {
            discrepancies++;
          }
        }

        if (actualDelta < -1e-6) {
          // Reverse segment from i+1 to j
          const segment = currentTour.slice(i + 1, j + 1).reverse();
          currentTour = [
            ...currentTour.slice(0, i + 1),
            ...segment,
            ...currentTour.slice(j + 1),
          ];

          movesAccepted++;
          improved = true;
          break;
        }
      }
      if (improved) break;
    }
  }

  return {
    tour: currentTour,
    cost: calculateTourCost(currentTour, matrix),
    movesAccepted,
    symmetryGuardTriggered: !isSymmetric,
    evaluationComplexity: !isSymmetric && !forceNaive ? 'O(k) Honest Asymmetric' : 'O(1) Textbook',
    asymmetryDiscrepanciesDetected: discrepancies,
  };
}

/**
 * Diagnostic tool: Demonstrates the exact numerical failure of the 4-term formula on asymmetric matrices
 */
export function demonstrateAsymmetryTrap(
  tour: number[],
  asymmetricMatrix: number[][]
): {
  stopA: number;
  stopB: number;
  stopC: number;
  stopD: number;
  segment: number[];
  naivePredictedDelta: number;
  actualDelta: number;
  errorMetres: number;
  explanation: string;
} {
  const n = tour.length - 1;
  for (let i = 0; i < n - 2; i++) {
    for (let j = i + 2; j < n; j++) {
      const a = tour[i];
      const b = tour[i + 1];
      const c = tour[j];
      const d = tour[j + 1];

      const naiveDelta = asymmetricMatrix[a][c] + asymmetricMatrix[b][d] - asymmetricMatrix[a][b] - asymmetricMatrix[c][d];

      let internalDelta = 0;
      for (let p = i + 1; p < j; p++) {
        const u = tour[p];
        const v = tour[p + 1];
        internalDelta += asymmetricMatrix[v][u] - asymmetricMatrix[u][v];
      }

      const actualDelta = naiveDelta + internalDelta;
      const errorMetres = Math.abs(actualDelta - naiveDelta);

      if (errorMetres > 50) {
        return {
          stopA: a,
          stopB: b,
          stopC: c,
          stopD: d,
          segment: tour.slice(i + 1, j + 1),
          naivePredictedDelta: naiveDelta,
          actualDelta,
          errorMetres,
          explanation: `Reversing segment [${tour.slice(i + 1, j + 1).join('→')}] on this one-way street network costs ${internalDelta > 0 ? '+' : ''}${internalDelta}m internally. The textbook 4-term formula falsely predicted a change of ${naiveDelta}m, resulting in a ${errorMetres}m error!`,
        };
      }
    }
  }

  return {
    stopA: tour[0],
    stopB: tour[1],
    stopC: tour[2],
    stopD: tour[3],
    segment: [tour[1], tour[2]],
    naivePredictedDelta: 0,
    actualDelta: 0,
    errorMetres: 0,
    explanation: 'No significant asymmetry discrepancy found for this short path.',
  };
}
