/**
 * Waybill — instance sources for the web app.
 *
 * TSPLIB instances come from `instances.generated.ts`, which is produced by
 * `python -m tools.generate_web_data` from the checksummed files in data/tsplib/.
 * Each was verified before export: its published optimal tour was scored with
 * this project's own distance implementation and matched exactly.
 *
 * Coordinates are never typed into this file. An earlier version of this project
 * inlined them and had 17 of 52 wrong in berlin52 — the published optimal tour
 * scored 16,883 against a published 7,542, and every downstream gap was
 * meaningless while looking entirely reasonable.
 *
 * The courier instances below are SYNTHETIC demos. They make no benchmark claim
 * and have no published optimum, and their provenance strings say so.
 */

import { DistanceMatrix, Instance, ProblemType, Stop, Vehicle } from '../../types';
import {
  createAsymmetricRoadMatrix,
  createEuclideanMatrix,
  createHaversineMatrix,
} from '../distance/matrix';
import { TSPLIB_INSTANCES } from '../../data/instances.generated';

export type TsplibName = 'berlin52' | 'eil51' | 'st70';

/**
 * Build a TSP instance from verified TSPLIB data.
 *
 * Uses EUC_2D, the convention those instances declare. Note that TSPLIB's nint
 * is round-half-away-from-zero; JavaScript's Math.round matches it for
 * non-negative values, which is why createEuclideanMatrix is correct here.
 */
export function createTsplibInstance(name: TsplibName): Instance {
  const data = TSPLIB_INSTANCES[name];
  if (!data) {
    throw new Error(
      `Unknown TSPLIB instance '${name}'. Available: ${Object.keys(TSPLIB_INSTANCES).join(', ')}. ` +
      `Add it to EXPORTED in tools/generate_web_data.py and regenerate — do not type coordinates here.`
    );
  }

  const stops: Stop[] = data.coords.map((coord, idx) => ({
    id: idx,
    name: idx === 0 ? 'Depot' : `Stop #${idx}`,
    x: coord[0],
    y: coord[1],
    demand: idx === 0 ? 0 : 1,
    serviceTimeSec: 0,
    isDepot: idx === 0,
  }));

  const matrix = createEuclideanMatrix(stops);

  return {
    id: `tsplib-${data.name}`,
    name: data.displayName,
    type: 'TSP',
    stops,
    vehicles: [
      { id: 1, name: 'Salesman', capacity: Number.MAX_SAFE_INTEGER, maxShiftSec: Number.MAX_SAFE_INTEGER, depotId: 0, color: '#3b82f6' },
    ],
    depot: stops[0],
    distanceMatrix: matrix,
    knownOptimum: data.publishedOptimum,
    source: `${data.source} · ${data.edgeWeightType} · verified against published optimum`,
    description: `${data.dimension} nodes. Published optimum ${data.publishedOptimum}, reproduced exactly by this project's own scorer.`,
  };
}

export function createSanFranciscoCourierInstance(): Instance {
  // SF Downtown / SoMa delivery zone: lat ~ 37.78, lng ~ -122.41
  const baseLat = 37.785;
  const baseLng = -122.405;

  const names = [
    'Depot (Distribution Hub - 4th & Mission)',
    '101 California Tower', 'Salesforce Transit Center', 'Ferry Building Market',
    'Rincon Hill Parcels', 'South Park Offices', 'Oracle Park Deliveries',
    'Mission Bay Biotech', 'Showplace Square Design', 'Potrero Hill Residences',
    '24th St Mission Corridor', 'Dolores Heights Medical', 'Castro Street Boutiques',
    'Lower Haight Cafe Supplies', 'Civic Center Gov Annex', 'Mid-Market Tech HQ',
    'Union Square Luxury Retail', 'Chinatown Grant Ave', 'North Beach Culinary',
    'Financial District Apex', 'Embarcadero Center 4', 'Telegraph Hill Studio',
    'Pier 39 Logistics', 'Fisherman Wharf Depot', 'Russian Hill Apartments',
    'Nob Hill Hotel Hub', 'Polk Gulch Pharmacy', 'Van Ness Auto Row',
    'Japantown Peace Plaza', 'Western Addition Hub'
  ];

  const stops: Stop[] = names.map((name, idx) => {
    // Generate semi-realistic street coordinates
    const row = Math.floor(idx / 5);
    const col = idx % 5;
    const lat = baseLat + (row - 2.5) * 0.008 + (Math.sin(idx * 7) * 0.002);
    const lng = baseLng + (col - 2) * 0.009 + (Math.cos(idx * 11) * 0.002);

    // Realistic time windows: staggered shifts (08:30 to 17:00)
    // Morning window (09:00 - 11:30) vs Afternoon window (13:00 - 16:30)
    const isMorning = idx % 2 === 0;
    const startSec = isMorning ? 32400 + (idx % 3) * 1800 : 46800 + (idx % 3) * 1800;
    const endSec = startSec + 7200; // 2 hour window

    return {
      id: idx,
      name,
      x: col * 120 + 50,
      y: row * 100 + 50,
      lat,
      lng,
      demand: idx === 0 ? 0 : 1 + (idx % 4), // 1 to 4 parcels
      window: idx === 0 ? undefined : { startSec, endSec },
      serviceTimeSec: idx === 0 ? 0 : 240 + (idx % 3) * 60, // 4 to 6 mins
      isDepot: idx === 0,
    };
  });

  const matrix = createAsymmetricRoadMatrix(stops, 0.35); // 35% asymmetry on SF one-way grid

  return {
    id: 'cvrptw-sf-30',
    name: 'San Francisco Metro Fleet (30 Stops · CVRPTW)',
    type: 'CVRPTW',
    stops,
    vehicles: [
      { id: 1, name: 'Van Alpha (North Zone)', capacity: 16, maxShiftSec: 28800, depotId: 0, color: '#3b82f6' },
      { id: 2, name: 'Van Bravo (South Zone)', capacity: 16, maxShiftSec: 28800, depotId: 0, color: '#10b981' },
      { id: 3, name: 'Van Charlie (East Waterfront)', capacity: 16, maxShiftSec: 28800, depotId: 0, color: '#f59e0b' },
      { id: 4, name: 'Van Delta (West Corridors)', capacity: 16, maxShiftSec: 28800, depotId: 0, color: '#ec4899' },
    ],
    depot: stops[0],
    distanceMatrix: matrix,
    source: 'SYNTHETIC — formula-generated coordinates and asymmetry. Not OSRM, not real road data.',
    description: '30 parcel stops across 4 delivery vans with strict 2-hour hard time windows, service times, and asymmetric street matrix.',
  };
}

export function createManhattan150CourierInstance(): Instance {
  const stops: Stop[] = [];
  // Depot at Midtown Manhattan
  stops.push({
    id: 0,
    name: 'Midtown Hub Depot (W 34th St)',
    x: 400,
    y: 350,
    lat: 40.7505,
    lng: -73.9934,
    demand: 0,
    serviceTimeSec: 0,
    isDepot: true,
  });

  // 150 stops across Manhattan grid (from Lower Manhattan to Central Park North)
  for (let i = 1; i <= 150; i++) {
    const street = 14 + (i % 80); // 14th St to 94th St
    const avenue = 1 + ((i * 3) % 11); // 1st Ave to 11th Ave
    const lat = 40.710 + (street / 80) * 0.08;
    const lng = -74.010 + (avenue / 11) * 0.045;

    // Time window
    const windowBucket = i % 4;
    const startSec = 30600 + windowBucket * 7200; // 08:30, 10:30, 12:30, 14:30
    const endSec = startSec + 9000; // 2.5 hour window

    stops.push({
      id: i,
      name: `Delivery #${i} (E ${street}th & Ave ${avenue})`,
      x: avenue * 65 + 30,
      y: (street - 10) * 8 + 20,
      lat,
      lng,
      demand: 1 + (i % 3),
      window: { startSec, endSec },
      serviceTimeSec: 180, // 3 minutes at door
      isDepot: false,
    });
  }

  const matrix = createAsymmetricRoadMatrix(stops, 0.4);

  return {
    id: 'cvrptw-manhattan-150',
    name: 'Manhattan High-Density Dispatch (150 Stops · 6 Vans)',
    type: 'CVRPTW',
    stops,
    vehicles: [
      { id: 1, name: 'Fleet 101', capacity: 35, maxShiftSec: 32400, depotId: 0, color: '#3b82f6' },
      { id: 2, name: 'Fleet 102', capacity: 35, maxShiftSec: 32400, depotId: 0, color: '#10b981' },
      { id: 3, name: 'Fleet 103', capacity: 35, maxShiftSec: 32400, depotId: 0, color: '#f59e0b' },
      { id: 4, name: 'Fleet 104', capacity: 35, maxShiftSec: 32400, depotId: 0, color: '#8b5cf6' },
      { id: 5, name: 'Fleet 105', capacity: 35, maxShiftSec: 32400, depotId: 0, color: '#ec4899' },
      { id: 6, name: 'Fleet 106', capacity: 35, maxShiftSec: 32400, depotId: 0, color: '#06b6d4' },
    ],
    depot: stops[0],
    distanceMatrix: matrix,
    source: 'High-Density 150-stop Manhattan Courier Grid',
    description: 'Realistic 150-stop full courier day. Demonstrates partitioning complexity and independent feasibility gating.',
  };
}

// ==========================================
// 3. SYNTHETIC & EXACT VALIDATION INSTANCES
// ==========================================

export function generateRandomInstance(
  n: number,
  type: ProblemType = 'TSP',
  symmetric = true,
  seed = 42
): Instance {
  let s = seed;
  const pseudoRandom = () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };

  const stops: Stop[] = [];
  stops.push({
    id: 0,
    name: 'Depot',
    x: 400,
    y: 300,
    demand: 0,
    serviceTimeSec: 0,
    isDepot: true,
  });

  for (let i = 1; i < n; i++) {
    const angle = pseudoRandom() * Math.PI * 2;
    const radius = 50 + pseudoRandom() * 250;
    const x = Math.round(400 + Math.cos(angle) * radius);
    const y = Math.round(300 + Math.sin(angle) * radius);

    const startSec = 32400 + Math.floor(pseudoRandom() * 4) * 3600;
    const endSec = startSec + 7200;

    stops.push({
      id: i,
      name: `Stop #${i}`,
      x,
      y,
      demand: 1 + Math.floor(pseudoRandom() * 3),
      window: type === 'CVRPTW' ? { startSec, endSec } : undefined,
      serviceTimeSec: 240,
      isDepot: false,
    });
  }

  const matrix = symmetric
    ? createEuclideanMatrix(stops)
    : createAsymmetricRoadMatrix(stops, 0.3);

  const vehicleCount = type === 'TSP' ? 1 : Math.max(2, Math.ceil(n / 6));
  const vehicles: Vehicle[] = [];
  const palette = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#e11d48', '#14b8a6'];

  for (let v = 1; v <= vehicleCount; v++) {
    vehicles.push({
      id: v,
      name: `Van ${v}`,
      capacity: Math.max(10, Math.ceil((n * 2) / vehicleCount)),
      maxShiftSec: 28800,
      depotId: 0,
      color: palette[(v - 1) % palette.length],
    });
  }

  return {
    id: `random-${n}-${type.toLowerCase()}-${symmetric ? 'sym' : 'asym'}`,
    name: `Seeded ${type} (${n} Stops · ${symmetric ? 'Symmetric' : 'Asymmetric'})`,
    type,
    stops,
    vehicles,
    depot: stops[0],
    distanceMatrix: matrix,
    source: `Seeded Generator (Seed: ${seed})`,
    description: `Configurable benchmark test instance with n=${n} stops.`,
  };
}
