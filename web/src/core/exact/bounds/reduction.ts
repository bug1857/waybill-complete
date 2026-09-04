/**
 * Waybill — Reduced-Cost Matrix Lower Bound (Little et al.) (§05, §06)
 * Computes lower bound by reducing matrix rows and columns by their minimum elements.
 */

export function computeReducedCostBound(
  matrix: number[][],
  visited: boolean[],
  lastNode: number,
  startNode = 0
): { lowerBound: number; reducedMatrix: number[][] } {
  const n = matrix.length;
  // Deep clone matrix
  const m: number[][] = matrix.map((row) => [...row]);

  // Set forbidden transitions to Infinity
  for (let i = 0; i < n; i++) {
    m[i][i] = Infinity;
    if (visited[i] && i !== lastNode && i !== startNode) {
      for (let j = 0; j < n; j++) {
        m[i][j] = Infinity;
        m[j][i] = Infinity;
      }
    }
  }

  let bound = 0;

  // 1. Row reduction
  for (let i = 0; i < n; i++) {
    if (visited[i] && i !== lastNode) continue;
    let minVal = Infinity;
    for (let j = 0; j < n; j++) {
      if (m[i][j] < minVal) {
        minVal = m[i][j];
      }
    }
    if (minVal > 0 && minVal < Infinity) {
      bound += minVal;
      for (let j = 0; j < n; j++) {
        if (m[i][j] < Infinity) {
          m[i][j] -= minVal;
        }
      }
    }
  }

  // 2. Column reduction
  for (let j = 0; j < n; j++) {
    if (visited[j] && j !== startNode) continue;
    let minVal = Infinity;
    for (let i = 0; i < n; i++) {
      if (m[i][j] < minVal) {
        minVal = m[i][j];
      }
    }
    if (minVal > 0 && minVal < Infinity) {
      bound += minVal;
      for (let i = 0; i < n; i++) {
        if (m[i][j] < Infinity) {
          m[i][j] -= minVal;
        }
      }
    }
  }

  return { lowerBound: bound, reducedMatrix: m };
}
