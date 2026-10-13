/**
 * Waybill — Hungarian (Assignment Problem) Lower Bound (§05, §06)
 * Solves the Linear Sum Assignment Problem (LAP) on distance matrix with diag=Infinity.
 * Provides a significantly tighter lower bound than basic matrix reduction.
 */

export function computeHungarianBound(matrix: number[][], visited: boolean[], lastNode: number, startNode = 0): number {
  const n = matrix.length;
  // Extract remaining nodes
  const unvisited: number[] = [];
  for (let i = 0; i < n; i++) {
    if (!visited[i] || i === lastNode || i === startNode) {
      unvisited.push(i);
    }
  }

  const k = unvisited.length;
  if (k <= 1) return 0;

  // Build submatrix
  const cost: number[][] = Array.from({ length: k }, () => new Array(k).fill(0));
  for (let i = 0; i < k; i++) {
    const u = unvisited[i];
    for (let j = 0; j < k; j++) {
      const v = unvisited[j];
      if (u === v || (u === lastNode && v === startNode && k > 2)) {
        cost[i][j] = 1e9; // forbid self loop or early closure
      } else {
        cost[i][j] = matrix[u][v];
      }
    }
  }

  return solveAssignmentProblem(cost);
}

/**
 * Jonker-Volgenant / Hungarian shortest path augmentation algorithm O(k^3)
 */
function solveAssignmentProblem(cost: number[][]): number {
  const n = cost.length;
  const u = new Float64Array(n + 1);
  const v = new Float64Array(n + 1);
  const p = new Int32Array(n + 1);
  const way = new Int32Array(n + 1);

  for (let i = 1; i <= n; i++) {
    p[0] = i;
    let j0 = 0;
    const minv = new Float64Array(n + 1).fill(Infinity);
    const used = new Uint8Array(n + 1).fill(0);

    do {
      used[j0] = 1;
      const i0 = p[j0];
      let delta = Infinity;
      let j1 = 0;

      for (let j = 1; j <= n; j++) {
        if (!used[j]) {
          const cur = cost[i0 - 1][j - 1] - u[i0] - v[j];
          if (cur < minv[j]) {
            minv[j] = cur;
            way[j] = j0;
          }
          if (minv[j] < delta) {
            delta = minv[j];
            j1 = j;
          }
        }
      }

      for (let j = 0; j <= n; j++) {
        if (used[j]) {
          u[p[j]] += delta;
          v[j] -= delta;
        } else {
          minv[j] -= delta;
        }
      }
      j0 = j1;
    } while (p[j0] !== 0);

    do {
      const j1 = way[j0];
      p[j0] = p[j1];
      j0 = j1;
    } while (j0 !== 0);
  }

  let totalCost = -v[0];
  if (totalCost >= 1e8) return 0;
  return Math.max(0, Math.round(totalCost));
}
