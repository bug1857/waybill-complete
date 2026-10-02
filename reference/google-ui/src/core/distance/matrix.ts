/**
 * Waybill — Distance Matrix and Symmetry Engine (§04, §07)
 * Enforces integer metres/seconds, strict isSymmetric check, and matrix hashing.
 */

import { DistanceMatrix, Stop } from '../../types';

/**
 * FNV-1a 32-bit hash for distance matrices
 */
export function hashMatrix(matrix: number[][]): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < matrix.length; i++) {
    for (let j = 0; j < matrix[i].length; j++) {
      const val = matrix[i][j];
      hash ^= (val & 0xff);
      hash = Math.imul(hash, 0x01000193);
      hash ^= ((val >> 8) & 0xff);
      hash = Math.imul(hash, 0x01000193);
      hash ^= ((val >> 16) & 0xff);
      hash = Math.imul(hash, 0x01000193);
      hash ^= ((val >> 24) & 0xff);
      hash = Math.imul(hash, 0x01000193);
    }
  }
  return '0x' + (hash >>> 0).toString(16).padStart(8, '0');
}

/**
 * Check whether a matrix is strictly symmetric: d(i,j) === d(j,i)
 */
export function checkSymmetry(matrix: number[][]): boolean {
  const n = matrix.length;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (matrix[i][j] !== matrix[j][i]) {
        return false;
      }
    }
  }
  return true;
}

/**
 * TSPLIB EUC_2D exact distance convention: round to nearest integer
 * d(i, j) = round( sqrt( (x_i - x_j)^2 + (y_i - y_j)^2 ) )
 */
export function createEuclideanMatrix(stops: Stop[]): DistanceMatrix {
  const n = stops.length;
  const matrix: number[][] = Array.from({ length: n }, () => new Array(n).fill(0));

  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      if (i === j) {
        matrix[i][j] = 0;
      } else {
        const dx = stops[i].x - stops[j].x;
        const dy = stops[i].y - stops[j].y;
        matrix[i][j] = Math.round(Math.sqrt(dx * dx + dy * dy));
      }
    }
  }

  const isSymmetric = checkSymmetry(matrix);
  return {
    matrix,
    isSymmetric,
    hash: hashMatrix(matrix),
    // TSPLIB coordinates are unitless; the EUC_2D convention yields an abstract
    // integer cost. Calling it metres and dividing by 1000 to show "km" is a
    // category error that makes every displayed figure wrong by a factor of 1000.
    units: 'tsplib_units',
    provider: 'EUCLIDEAN_2D',
  };
}

/**
 * Haversine geographic distance in integer metres (Symmetric)
 */
export function createHaversineMatrix(stops: Stop[]): DistanceMatrix {
  const n = stops.length;
  const matrix: number[][] = Array.from({ length: n }, () => new Array(n).fill(0));
  const R = 6371000; // Earth radius in metres

  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      if (i === j) {
        matrix[i][j] = 0;
      } else {
        const lat1 = (stops[i].lat ?? stops[i].y) * (Math.PI / 180);
        const lon1 = (stops[i].lng ?? stops[i].x) * (Math.PI / 180);
        const lat2 = (stops[j].lat ?? stops[j].y) * (Math.PI / 180);
        const lon2 = (stops[j].lng ?? stops[j].x) * (Math.PI / 180);

        const dLat = lat2 - lat1;
        const dLon = lon2 - lon1;

        const a =
          Math.sin(dLat / 2) * Math.sin(dLat / 2) +
          Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        // Direct Haversine * 1.3 road winding factor (standard benchmark approximation)
        matrix[i][j] = Math.round(R * c * 1.3);
      }
    }
  }

  return {
    matrix,
    isSymmetric: true,
    hash: hashMatrix(matrix),
    units: 'metres',
    provider: 'HAVERSINE',
  };
}

/**
 * SYNTHETIC asymmetric matrix generator.
 *
 * Formula-generated asymmetry for demo purposes. It is NOT OSRM and NOT real
 * road data: direction dependence comes from Math.sin(i*13 + j*7), not from a
 * street network. Real road matrices come from adapters/distance/osrm.py on
 * the Python side, where five Monaco stops gave 10 of 10 asymmetric pairs with
 * a 130s largest gap.
 *
 * The provider string says SYNTHETIC_ASYMMETRIC so nothing downstream can
 * mistake this for measured data.
 * d(A, B) != d(B, A).
 */
export function createAsymmetricRoadMatrix(stops: Stop[], asymmetryFactor = 0.25): DistanceMatrix {
  const n = stops.length;
  const matrix: number[][] = Array.from({ length: n }, () => new Array(n).fill(0));

  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      if (i === j) {
        matrix[i][j] = 0;
      } else {
        const dx = (stops[i].lng ?? stops[i].x) - (stops[j].lng ?? stops[j].x);
        const dy = (stops[i].lat ?? stops[i].y) - (stops[j].lat ?? stops[j].y);
        // Manhattan-like street grid component + Euclidean base
        const manhattan = Math.abs(dx) + Math.abs(dy);
        const euclidean = Math.sqrt(dx * dx + dy * dy);
        const baseDist = Math.round((0.7 * manhattan + 0.3 * euclidean) * 111320); // deg to meters approx

        // Deterministic directional asymmetry:
        // Going North/East vs South/West has one-way avenues and traffic directionality
        const dirPenalty = (Math.sin(i * 13 + j * 7) * 0.5 + 0.5);
        const oneWayFactor = 1.0 + asymmetryFactor * (dirPenalty - 0.5) * 2;
        
        // Add turn penalty when reversing between specific stop pairs
        const turnPenalty = ((i + j) % 3 === 0) ? 140 : 0; // 140m turn delay
        
        matrix[i][j] = Math.max(50, Math.round(baseDist * oneWayFactor + turnPenalty));
      }
    }
  }

  const isSymmetric = checkSymmetry(matrix);
  return {
    matrix,
    isSymmetric,
    hash: hashMatrix(matrix),
    units: 'metres',
    provider: 'SYNTHETIC_ASYMMETRIC',
  };
}
