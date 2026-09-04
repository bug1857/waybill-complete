/**
 * Waybill — Or-Opt and Relocate Local Search (§05, §07)
 * Moves segments of length k in {1, 2, 3} without reversing them.
 * Crucial property: Asymmetry-Safe. Remains O(1) evaluation even on real road networks.
 */

import { calculateTourCost } from '../eval/feasibility';

export interface LocalSearchResult {
  tour: number[];
  cost: number;
  movesAccepted: number;
}

/**
 * Or-opt iterative improvement on a TSP tour (starts and ends with 0)
 */
export function improveOrOpt(tour: number[], matrix: number[][], maxIterations = 500): LocalSearchResult {
  let currentTour = [...tour];
  if (currentTour.length < 5) {
    return { tour: currentTour, cost: calculateTourCost(currentTour, matrix), movesAccepted: 0 };
  }

  let improved = true;
  let movesAccepted = 0;
  let iterations = 0;
  const n = currentTour.length - 1; // number of stops including depot

  while (improved && iterations < maxIterations) {
    improved = false;
    iterations++;

    // Try segment lengths 3, 2, 1 (Or-Opt block sizes)
    for (const segLen of [3, 2, 1]) {
      for (let i = 1; i <= n - segLen; i++) {
        const j = i + segLen - 1;
        const u = currentTour[i - 1];
        const v = currentTour[i];
        const w = currentTour[j];
        const x = currentTour[j + 1];

        // Cost removed if segment [i..j] is removed
        const costRemoved = matrix[u][v] + matrix[w][x];
        const bridgeAdded = matrix[u][x];

        // Try inserting after position k
        for (let k = 0; k < n; k++) {
          if (k >= i - 1 && k <= j) continue;

          const p = currentTour[k];
          const q = currentTour[k + 1];

          // Move delta: (matrix[u][x] + matrix[p][v] + matrix[w][q]) - (matrix[u][v] + matrix[w][x] + matrix[p][q])
          const delta = (bridgeAdded + matrix[p][v] + matrix[w][q]) - (costRemoved + matrix[p][q]);

          if (delta < -1e-6) {
            // Perform relocation of segment [i..j] to after position k
            const segment = currentTour.slice(i, j + 1);
            const remaining = [...currentTour.slice(0, i), ...currentTour.slice(j + 1)];

            let insertPos = k + 1;
            if (k >= j) {
              insertPos = k + 1 - segLen;
            }

            currentTour = [
              ...remaining.slice(0, insertPos),
              ...segment,
              ...remaining.slice(insertPos),
            ];

            movesAccepted++;
            improved = true;
            break;
          }
        }
        if (improved) break;
      }
      if (improved) break;
    }
  }

  return {
    tour: currentTour,
    cost: calculateTourCost(currentTour, matrix),
    movesAccepted,
  };
}
