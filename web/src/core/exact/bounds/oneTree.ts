/**
 * Waybill — 1-Tree Lower Bound with Subgradient Ascent (Held–Karp Relaxation) (§05, §06)
 * Computes the MST on V \ {1} + 2 cheapest edges to node 1.
 * Uses subgradient ascent over node multipliers pi_i to dramatically tighten the bound.
 */

export function computeOneTreeBound(
  matrix: number[][],
  visited: boolean[],
  lastNode: number,
  startNode = 0,
  incumbentUpper = Infinity,
  maxAscentIterations = 15
): { lowerBound: number; isTour: boolean } {
  const n = matrix.length;
  const unvisited: number[] = [];
  for (let i = 0; i < n; i++) {
    if (!visited[i] || i === lastNode || i === startNode) {
      unvisited.push(i);
    }
  }

  const k = unvisited.length;
  if (k <= 2) {
    if (k === 2) {
      return { lowerBound: matrix[unvisited[0]][unvisited[1]] + matrix[unvisited[1]][unvisited[0]], isTour: true };
    }
    return { lowerBound: 0, isTour: true };
  }

  // Node potentials for subgradient ascent
  const pi = new Float64Array(k).fill(0);
  let bestLb = -Infinity;
  let stepSize = 1.0;

  for (let iter = 0; iter < maxAscentIterations; iter++) {
    // 1. Build modified distance matrix: c'[i][j] = c[i][j] + pi[i] + pi[j]
    // 2. Compute 1-tree on unvisited nodes using unvisited[0] as the special 1-tree hub
    const hub = 0; // index in unvisited
    const hubRealNode = unvisited[0];

    // Kruskal or Prim MST on remaining nodes (indices 1 to k-1)
    const mstEdges: { u: number; v: number; cost: number }[] = [];
    const inMst = new Uint8Array(k).fill(0);
    const minEdgeCost = new Float64Array(k).fill(Infinity);
    const minEdgeFrom = new Int32Array(k).fill(-1);

    inMst[1] = 1;
    for (let j = 2; j < k; j++) {
      const uNode = unvisited[1];
      const vNode = unvisited[j];
      const c = matrix[uNode][vNode] + pi[1] + pi[j];
      minEdgeCost[j] = c;
      minEdgeFrom[j] = 1;
    }

    let mstWeight = 0;
    const degrees = new Int32Array(k).fill(0);

    for (let step = 1; step < k - 1; step++) {
      let minVal = Infinity;
      let nextNode = -1;

      for (let j = 1; j < k; j++) {
        if (!inMst[j] && minEdgeCost[j] < minVal) {
          minVal = minEdgeCost[j];
          nextNode = j;
        }
      }

      if (nextNode === -1) break;
      inMst[nextNode] = 1;
      mstWeight += minVal;
      degrees[nextNode]++;
      degrees[minEdgeFrom[nextNode]]++;

      // Update edges from nextNode
      for (let j = 1; j < k; j++) {
        if (!inMst[j]) {
          const uNode = unvisited[nextNode];
          const vNode = unvisited[j];
          const c = matrix[uNode][vNode] + pi[nextNode] + pi[j];
          if (c < minEdgeCost[j]) {
            minEdgeCost[j] = c;
            minEdgeFrom[j] = nextNode;
          }
        }
      }
    }

    // 3. Find 2 cheapest edges from hub (index 0) to other nodes (indices 1 to k-1)
    let min1 = Infinity;
    let min2 = Infinity;
    let node1 = -1;
    let node2 = -1;

    for (let j = 1; j < k; j++) {
      const uNode = unvisited[0];
      const vNode = unvisited[j];
      const c = matrix[uNode][vNode] + pi[0] + pi[j];
      if (c < min1) {
        min2 = min1;
        node2 = node1;
        min1 = c;
        node1 = j;
      } else if (c < min2) {
        min2 = c;
        node2 = j;
      }
    }

    if (node1 !== -1) degrees[0]++, degrees[node1]++;
    if (node2 !== -1) degrees[0]++, degrees[node2]++;

    const oneTreeWeight = mstWeight + min1 + min2;
    let sumPi = 0;
    for (let i = 0; i < k; i++) sumPi += pi[i];

    const currentLb = Math.round(oneTreeWeight - 2 * sumPi);

    if (currentLb > bestLb) {
      bestLb = currentLb;
    }

    // Check if 1-tree is already a tour (all degrees == 2)
    let isTour = true;
    let subgradientNormSq = 0;
    for (let i = 0; i < k; i++) {
      const g = 2 - degrees[i];
      subgradientNormSq += g * g;
      if (degrees[i] !== 2) isTour = false;
    }

    if (isTour || subgradientNormSq === 0) {
      return { lowerBound: Math.max(0, bestLb), isTour: true };
    }

    // Subgradient step update
    const targetUb = incumbentUpper < Infinity ? incumbentUpper : bestLb * 1.15 + 10;
    stepSize = (targetUb - currentLb) / (subgradientNormSq + 1);

    for (let i = 0; i < k; i++) {
      const g = 2 - degrees[i];
      pi[i] += stepSize * g * 0.5;
    }
  }

  return { lowerBound: Math.max(0, bestLb), isTour: false };
}
