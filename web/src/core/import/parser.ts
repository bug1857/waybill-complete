/**
 * Waybill — Real Data Importer & Parser (CSV & JSON)
 * Converts arbitrary CSV/JSON stop lists or instances into validated Waybill CVRPTW Instances.
 */

import { DistanceMatrix, Instance, ProblemType, Stop, TimeWindow, Vehicle } from '../../types';
import {
  createAsymmetricRoadMatrix,
  createEuclideanMatrix,
  createHaversineMatrix,
  hashMatrix,
} from '../distance/matrix';

export interface FleetOptions {
  vehicleCount: number;
  vehicleCapacity: number;
  maxShiftHours: number;
  matrixMode: 'ASYMMETRIC_ROAD' | 'EUCLIDEAN' | 'HAVERSINE';
}

export interface ParseResult {
  success: boolean;
  instance?: Instance;
  errors: string[];
  warnings: string[];
  stats?: {
    stopCount: number;
    totalDemand: number;
    totalCapacity: number;
    hasTimeWindows: boolean;
    hasGpsCoords: boolean;
    isAsymmetric: boolean;
  };
}

/**
 * Parse a time string (e.g., "09:00", "9:30 AM", "14:45:00", or "32400") into seconds from midnight
 */
export function parseTimeToSeconds(timeStr: string | number | undefined): number | undefined {
  if (timeStr === undefined || timeStr === null || timeStr === '') return undefined;
  if (typeof timeStr === 'number') return timeStr;

  const str = String(timeStr).trim();
  // Pure seconds number
  if (/^\d+$/.test(str)) {
    return parseInt(str, 10);
  }

  // 12-hour AM/PM format (e.g., "09:30 AM", "2:15 PM")
  const ampmMatch = str.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)?$/i);
  if (ampmMatch) {
    let hours = parseInt(ampmMatch[1], 10);
    const minutes = parseInt(ampmMatch[2], 10);
    const seconds = ampmMatch[3] ? parseInt(ampmMatch[3], 10) : 0;
    const meridian = ampmMatch[4]?.toUpperCase();

    if (meridian === 'PM' && hours < 12) hours += 12;
    if (meridian === 'AM' && hours === 12) hours = 0;

    return hours * 3600 + minutes * 60 + seconds;
  }

  return undefined;
}

/**
 * Format seconds from midnight into readable "HH:MM" format
 */
export function formatSecondsToTime(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
}

/**
 * Parses a standard CSV string with header detection
 */
export function parseCsvData(
  csvText: string,
  fleetOptions: FleetOptions,
  instanceName = 'Custom Uploaded Fleet'
): ParseResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!csvText || !csvText.trim()) {
    return { success: false, errors: ['CSV content is empty.'], warnings: [] };
  }

  const lines = csvText
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && !l.startsWith('#'));

  if (lines.length < 2) {
    return {
      success: false,
      errors: ['CSV must have a header row and at least 2 stop records.'],
      warnings: [],
    };
  }

  // Parse header row
  const header = parseCsvLine(lines[0]).map((h) =>
    h.toLowerCase().trim().replace(/[\s_-]+/g, '')
  );

  const colMap = {
    name: findColIndex(header, ['name', 'label', 'address', 'stop', 'stopname', 'location', 'title']),
    x: findColIndex(header, ['x', 'xcoord', 'posx', 'coordx']),
    y: findColIndex(header, ['y', 'ycoord', 'posy', 'coordy']),
    lat: findColIndex(header, ['lat', 'latitude', 'gpslat', 'y', 'wgs84lat']),
    lng: findColIndex(header, ['lng', 'lon', 'longitude', 'long', 'gpslng', 'x', 'wgs84lng', 'wgs84lon']),
    demand: findColIndex(header, ['demand', 'parcels', 'quantity', 'load', 'weight', 'count', 'boxes', 'packages', 'pkg']),
    windowStart: findColIndex(header, ['windowstart', 'twstart', 'starttime', 'readytime', 'open', 'opentime', 'start', 'earliest']),
    windowEnd: findColIndex(header, ['windowend', 'twend', 'duetime', 'closetime', 'close', 'end', 'latest']),
    serviceTime: findColIndex(header, ['servicetime', 'servicetimesec', 'service', 'duration', 'stoptime', 'dwelltime']),
    isDepot: findColIndex(header, ['isdepot', 'depot', 'ishub', 'hub', 'type']),
  };

  const rawStops: Array<{
    id: number;
    name: string;
    x?: number;
    y?: number;
    lat?: number;
    lng?: number;
    demand: number;
    window?: TimeWindow;
    serviceTimeSec: number;
    isDepot: boolean;
  }> = [];

  let hasGps = false;
  let hasCartesian = false;
  let hasWindows = false;

  for (let i = 1; i < lines.length; i++) {
    const row = parseCsvLine(lines[i]);
    if (row.length === 0 || row.every((c) => !c.trim())) continue;

    const stopId = i - 1;
    const nameVal = colMap.name !== -1 ? row[colMap.name]?.trim() : `Location #${stopId}`;
    const name = nameVal || `Location #${stopId}`;

    // Coordinates
    let xVal = colMap.x !== -1 ? parseFloat(row[colMap.x]) : undefined;
    let yVal = colMap.y !== -1 ? parseFloat(row[colMap.y]) : undefined;
    let latVal = colMap.lat !== -1 ? parseFloat(row[colMap.lat]) : undefined;
    let lngVal = colMap.lng !== -1 ? parseFloat(row[colMap.lng]) : undefined;

    if (isNaN(xVal!)) xVal = undefined;
    if (isNaN(yVal!)) yVal = undefined;
    if (isNaN(latVal!)) latVal = undefined;
    if (isNaN(lngVal!)) lngVal = undefined;

    // Check if lat/lng are plausible GPS coordinates (-90..90, -180..180)
    if (latVal !== undefined && lngVal !== undefined && Math.abs(latVal) <= 90 && Math.abs(lngVal) <= 180) {
      hasGps = true;
    }

    if (xVal !== undefined && yVal !== undefined) {
      hasCartesian = true;
    }

    // Demand
    let demand = 1;
    if (colMap.demand !== -1 && row[colMap.demand]) {
      const parsedDemand = parseInt(row[colMap.demand], 10);
      if (!isNaN(parsedDemand) && parsedDemand >= 0) demand = parsedDemand;
    }

    // Service Time
    let serviceTimeSec = 300; // default 5 mins
    if (colMap.serviceTime !== -1 && row[colMap.serviceTime]) {
      const parsedSec = parseTimeToSeconds(row[colMap.serviceTime]);
      if (parsedSec !== undefined) serviceTimeSec = parsedSec;
    }

    // Time Windows
    let window: TimeWindow | undefined = undefined;
    if (colMap.windowStart !== -1 && colMap.windowEnd !== -1) {
      const startSec = parseTimeToSeconds(row[colMap.windowStart]);
      const endSec = parseTimeToSeconds(row[colMap.windowEnd]);
      if (startSec !== undefined && endSec !== undefined && endSec > startSec) {
        window = { startSec, endSec };
        hasWindows = true;
      }
    }

    // Depot flag
    let isDepot = stopId === 0;
    if (colMap.isDepot !== -1 && row[colMap.isDepot]) {
      const val = row[colMap.isDepot].toLowerCase().trim();
      if (val === '1' || val === 'true' || val === 'yes' || val === 'depot' || val === 'hub') {
        isDepot = true;
      }
    }

    rawStops.push({
      id: stopId,
      name,
      x: xVal,
      y: yVal,
      lat: latVal,
      lng: lngVal,
      demand: isDepot ? 0 : demand,
      window: isDepot ? undefined : window,
      serviceTimeSec: isDepot ? 0 : serviceTimeSec,
      isDepot,
    });
  }

  if (rawStops.length < 2) {
    return {
      success: false,
      errors: ['At least 2 valid locations (1 depot + 1 delivery stop) are required.'],
      warnings,
    };
  }

  // Ensure first stop is marked as depot if none marked
  const depotIdx = rawStops.findIndex((s) => s.isDepot);
  if (depotIdx === -1) {
    rawStops[0].isDepot = true;
    rawStops[0].demand = 0;
    warnings.push('No depot explicitly marked; first stop was designated as the fleet depot.');
  }

  // Normalize Display Coordinates (x, y) if only GPS is provided
  const stops: Stop[] = normalizeDisplayCoordinates(rawStops);

  // Generate fleet vehicles
  const vehicleColors = ['#1A3A5B', '#234E3E', '#B84A39', '#C27803', '#5A2A42', '#3D4852', '#0D9488', '#E11D48'];
  const vehicles: Vehicle[] = Array.from({ length: fleetOptions.vehicleCount }, (_, idx) => ({
    id: idx + 1,
    name: `Van #${idx + 1}`,
    capacity: fleetOptions.vehicleCapacity,
    maxShiftSec: fleetOptions.maxShiftHours * 3600,
    depotId: 0,
    color: vehicleColors[idx % vehicleColors.length],
  }));

  // Construct Distance Matrix
  let distanceMatrix: DistanceMatrix;
  if (fleetOptions.matrixMode === 'ASYMMETRIC_ROAD') {
    distanceMatrix = createAsymmetricRoadMatrix(stops, 0.3);
  } else if (fleetOptions.matrixMode === 'HAVERSINE' && hasGps) {
    distanceMatrix = createHaversineMatrix(stops);
  } else {
    distanceMatrix = createEuclideanMatrix(stops);
  }

  const totalDemand = stops.reduce((sum, s) => sum + s.demand, 0);
  const totalCapacity = vehicles.reduce((sum, v) => sum + v.capacity, 0);

  if (totalDemand > totalCapacity) {
    warnings.push(
      `Total parcel demand (${totalDemand}) exceeds total fleet capacity (${totalCapacity}). Some orders may be infeasible or require multiple trips.`
    );
  }

  const problemType: ProblemType = hasWindows ? 'CVRPTW' : vehicles.length > 1 ? 'CVRP' : 'TSP';

  const instance: Instance = {
    id: `custom-${Date.now()}`,
    name: instanceName,
    type: problemType,
    stops,
    vehicles,
    depot: stops[0],
    distanceMatrix,
    description: `User-imported dataset with ${stops.length} locations (${totalDemand} parcels total) across ${vehicles.length} fleet vehicles.`,
    source: 'Custom CSV File Upload',
  };

  return {
    success: true,
    instance,
    errors: [],
    warnings,
    stats: {
      stopCount: stops.length,
      totalDemand,
      totalCapacity,
      hasTimeWindows: hasWindows,
      hasGpsCoords: hasGps,
      isAsymmetric: !distanceMatrix.isSymmetric,
    },
  };
}

/**
 * Parses JSON format (either full Instance object, { stops, vehicles }, or Stop array)
 */
export function parseJsonData(
  jsonText: string,
  fleetOptions: FleetOptions,
  instanceName = 'Custom Uploaded Instance'
): ParseResult {
  const warnings: string[] = [];
  try {
    const data = JSON.parse(jsonText);

    // Case 1: Full Instance object provided
    if (data.stops && Array.isArray(data.stops) && data.stops.length >= 2) {
      const rawStops = data.stops.map((s: any, idx: number) => ({
        id: typeof s.id === 'number' ? s.id : idx,
        name: s.name || `Location #${idx}`,
        x: typeof s.x === 'number' ? s.x : undefined,
        y: typeof s.y === 'number' ? s.y : undefined,
        lat: typeof s.lat === 'number' ? s.lat : undefined,
        lng: typeof s.lng === 'number' ? s.lng : undefined,
        demand: typeof s.demand === 'number' ? s.demand : idx === 0 ? 0 : 1,
        serviceTimeSec: typeof s.serviceTimeSec === 'number' ? s.serviceTimeSec : idx === 0 ? 0 : 300,
        isDepot: s.isDepot ?? idx === 0,
        window: s.window && typeof s.window.startSec === 'number' && typeof s.window.endSec === 'number'
          ? s.window
          : undefined,
      }));

      const stops = normalizeDisplayCoordinates(rawStops);

      // Vehicles
      let vehicles: Vehicle[] = [];
      if (data.vehicles && Array.isArray(data.vehicles) && data.vehicles.length > 0) {
        vehicles = data.vehicles.map((v: any, idx: number) => ({
          id: typeof v.id === 'number' ? v.id : idx + 1,
          name: v.name || `Van #${idx + 1}`,
          capacity: typeof v.capacity === 'number' ? v.capacity : fleetOptions.vehicleCapacity,
          maxShiftSec: typeof v.maxShiftSec === 'number' ? v.maxShiftSec : fleetOptions.maxShiftHours * 3600,
          depotId: typeof v.depotId === 'number' ? v.depotId : 0,
          color: v.color || '#1A3A5B',
        }));
      } else {
        const vehicleColors = ['#1A3A5B', '#234E3E', '#B84A39', '#C27803', '#5A2A42'];
        vehicles = Array.from({ length: fleetOptions.vehicleCount }, (_, idx) => ({
          id: idx + 1,
          name: `Van #${idx + 1}`,
          capacity: fleetOptions.vehicleCapacity,
          maxShiftSec: fleetOptions.maxShiftHours * 3600,
          depotId: 0,
          color: vehicleColors[idx % vehicleColors.length],
        }));
      }

      // Distance Matrix
      let distanceMatrix: DistanceMatrix;
      if (
        data.distanceMatrix &&
        Array.isArray(data.distanceMatrix.matrix) &&
        data.distanceMatrix.matrix.length === stops.length
      ) {
        distanceMatrix = {
          matrix: data.distanceMatrix.matrix,
          isSymmetric: data.distanceMatrix.isSymmetric ?? true,
          hash: data.distanceMatrix.hash || hashMatrix(data.distanceMatrix.matrix),
          units: data.distanceMatrix.units || 'metres',
          provider: data.distanceMatrix.provider || 'EUCLIDEAN_2D',
        };
      } else if (fleetOptions.matrixMode === 'ASYMMETRIC_ROAD') {
        distanceMatrix = createAsymmetricRoadMatrix(stops, 0.3);
      } else {
        distanceMatrix = createEuclideanMatrix(stops);
      }

      const hasWindows = stops.some((s) => s.window !== undefined);
      const totalDemand = stops.reduce((sum, s) => sum + s.demand, 0);
      const totalCapacity = vehicles.reduce((sum, v) => sum + v.capacity, 0);

      const instance: Instance = {
        id: `custom-json-${Date.now()}`,
        name: data.name || instanceName,
        type: data.type || (hasWindows ? 'CVRPTW' : vehicles.length > 1 ? 'CVRP' : 'TSP'),
        stops,
        vehicles,
        depot: stops[0],
        distanceMatrix,
        description: data.description || `Custom JSON instance with ${stops.length} locations.`,
        source: 'Custom JSON Upload',
      };

      return {
        success: true,
        instance,
        errors: [],
        warnings,
        stats: {
          stopCount: stops.length,
          totalDemand,
          totalCapacity,
          hasTimeWindows: hasWindows,
          hasGpsCoords: stops.some((s) => s.lat !== undefined),
          isAsymmetric: !distanceMatrix.isSymmetric,
        },
      };
    }

    // Case 2: Array of Stop objects
    if (Array.isArray(data) && data.length >= 2) {
      const rawStops = data.map((s: any, idx: number) => ({
        id: idx,
        name: s.name || s.address || `Stop #${idx}`,
        x: typeof s.x === 'number' ? s.x : undefined,
        y: typeof s.y === 'number' ? s.y : undefined,
        lat: typeof s.lat === 'number' ? s.lat : typeof s.latitude === 'number' ? s.latitude : undefined,
        lng: typeof s.lng === 'number' ? s.lng : typeof s.longitude === 'number' ? s.longitude : undefined,
        demand: typeof s.demand === 'number' ? s.demand : idx === 0 ? 0 : 1,
        serviceTimeSec: typeof s.serviceTimeSec === 'number' ? s.serviceTimeSec : idx === 0 ? 0 : 300,
        isDepot: s.isDepot ?? idx === 0,
        window: s.window ?? (s.windowStart ? { startSec: parseTimeToSeconds(s.windowStart) || 32400, endSec: parseTimeToSeconds(s.windowEnd) || 39600 } : undefined),
      }));

      const stops = normalizeDisplayCoordinates(rawStops);
      const vehicleColors = ['#1A3A5B', '#234E3E', '#B84A39', '#C27803', '#5A2A42'];
      const vehicles: Vehicle[] = Array.from({ length: fleetOptions.vehicleCount }, (_, idx) => ({
        id: idx + 1,
        name: `Van #${idx + 1}`,
        capacity: fleetOptions.vehicleCapacity,
        maxShiftSec: fleetOptions.maxShiftHours * 3600,
        depotId: 0,
        color: vehicleColors[idx % vehicleColors.length],
      }));

      const distanceMatrix =
        fleetOptions.matrixMode === 'ASYMMETRIC_ROAD'
          ? createAsymmetricRoadMatrix(stops, 0.3)
          : createEuclideanMatrix(stops);

      const hasWindows = stops.some((s) => s.window !== undefined);
      const totalDemand = stops.reduce((sum, s) => sum + s.demand, 0);
      const totalCapacity = vehicles.reduce((sum, v) => sum + v.capacity, 0);

      const instance: Instance = {
        id: `custom-json-${Date.now()}`,
        name: instanceName,
        type: hasWindows ? 'CVRPTW' : vehicles.length > 1 ? 'CVRP' : 'TSP',
        stops,
        vehicles,
        depot: stops[0],
        distanceMatrix,
        description: `Imported array of ${stops.length} locations.`,
        source: 'Custom JSON Array Upload',
      };

      return {
        success: true,
        instance,
        errors: [],
        warnings,
        stats: {
          stopCount: stops.length,
          totalDemand,
          totalCapacity,
          hasTimeWindows: hasWindows,
          hasGpsCoords: stops.some((s) => s.lat !== undefined),
          isAsymmetric: !distanceMatrix.isSymmetric,
        },
      };
    }

    return {
      success: false,
      errors: ['Invalid JSON format. Expected either a full Instance object with a "stops" array or an array of stop records.'],
      warnings: [],
    };
  } catch (err: any) {
    return {
      success: false,
      errors: [`JSON syntax error: ${err.message}`],
      warnings: [],
    };
  }
}

/**
 * Normalizes Cartesian display coordinates (x, y) into a clean 100..700 SVG canvas view
 */
function normalizeDisplayCoordinates(rawStops: any[]): Stop[] {
  const hasGps = rawStops.every((s) => s.lat !== undefined && s.lng !== undefined);
  const hasXy = rawStops.every((s) => s.x !== undefined && s.y !== undefined);

  if (hasXy && !hasGps) {
    return rawStops.map((s, idx) => ({
      id: s.id ?? idx,
      name: s.name,
      x: s.x,
      y: s.y,
      demand: s.demand ?? (idx === 0 ? 0 : 1),
      window: s.window,
      serviceTimeSec: s.serviceTimeSec ?? (idx === 0 ? 0 : 300),
      isDepot: s.isDepot ?? idx === 0,
    }));
  }

  // If we have GPS coordinates (or missing XY), project lat/lng onto [60, 740] x [60, 480] canvas
  const lats = rawStops.map((s) => s.lat ?? 37.78);
  const lngs = rawStops.map((s) => s.lng ?? -122.41);

  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);

  const latSpan = maxLat - minLat || 0.01;
  const lngSpan = maxLng - minLng || 0.01;

  return rawStops.map((s, idx) => {
    const lat = s.lat ?? minLat;
    const lng = s.lng ?? minLng;

    // Invert lat for SVG Y (high lat = top of screen)
    const normX = Math.round(60 + ((lng - minLng) / lngSpan) * 680);
    const normY = Math.round(480 - ((lat - minLat) / latSpan) * 400);

    return {
      id: s.id ?? idx,
      name: s.name,
      x: s.x ?? normX,
      y: s.y ?? normY,
      lat: s.lat,
      lng: s.lng,
      demand: s.demand ?? (idx === 0 ? 0 : 1),
      window: s.window,
      serviceTimeSec: s.serviceTimeSec ?? (idx === 0 ? 0 : 300),
      isDepot: s.isDepot ?? idx === 0,
    };
  });
}

function parseCsvLine(line: string): string[] {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      result.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current);
  return result;
}

function findColIndex(header: string[], candidates: string[]): number {
  for (const c of candidates) {
    const idx = header.indexOf(c);
    if (idx !== -1) return idx;
  }
  return -1;
}

// ==========================================
// PRE-BUILT REAL-WORLD SAMPLE TEMPLATES
// ==========================================

export const SAMPLE_CSV_CONTENT = `name,lat,lng,demand,window_start,window_end,service_time_sec,is_depot
Central Distribution Depot,51.5134,-0.1285,0,08:00,18:00,0,true
Covent Garden Florist,51.5117,-0.1235,2,08:30,10:30,300,false
Soho Tech Studio,51.5138,-0.1337,3,09:00,11:30,240,false
Mayfair Boutique Gallery,51.5098,-0.1472,1,10:00,12:30,360,false
Piccadilly Bookshop,51.5091,-0.1368,4,11:00,13:30,300,false
Fitzrovia Culinary Supplies,51.5202,-0.1385,2,13:00,15:00,240,false
Bloomsbury Medical Annex,51.5225,-0.1265,3,13:30,15:30,360,false
Marylebone Design Studio,51.5188,-0.1532,2,14:00,16:30,300,false
St James Retail Exchange,51.5065,-0.1378,3,15:00,17:00,240,false
Holborn Legal Archives,51.5175,-0.1195,1,15:30,17:30,300,false`;

export const SAMPLE_JSON_CONTENT = `{
  "name": "Tokyo Express Courier Hub",
  "type": "CVRPTW",
  "stops": [
    { "id": 0, "name": "Shibuya Central Depot", "lat": 35.6580, "lng": 139.7016, "demand": 0, "serviceTimeSec": 0, "isDepot": true },
    { "id": 1, "name": "Omotesando Luxury Retail", "lat": 35.6652, "lng": 139.7123, "demand": 3, "serviceTimeSec": 300, "window": { "startSec": 32400, "endSec": 39600 } },
    { "id": 2, "name": "Roppongi Hills Tech Tower", "lat": 35.6604, "lng": 139.7292, "demand": 4, "serviceTimeSec": 360, "window": { "startSec": 34200, "endSec": 41400 } },
    { "id": 3, "name": "Ginza Fine Art Gallery", "lat": 35.6719, "lng": 139.7648, "demand": 2, "serviceTimeSec": 240, "window": { "startSec": 46800, "endSec": 54000 } },
    { "id": 4, "name": "Marunouchi Financial Apex", "lat": 35.6812, "lng": 139.7671, "demand": 5, "serviceTimeSec": 420, "window": { "startSec": 48600, "endSec": 55800 } },
    { "id": 5, "name": "Akihabara Logistics Hub", "lat": 35.6983, "lng": 139.7731, "demand": 3, "serviceTimeSec": 300, "window": { "startSec": 50400, "endSec": 57600 } },
    { "id": 6, "name": "Shinjuku West High-Rise", "lat": 35.6895, "lng": 139.6917, "demand": 4, "serviceTimeSec": 300, "window": { "startSec": 36000, "endSec": 43200 } },
    { "id": 7, "name": "Ebisu Garden Place Supplies", "lat": 35.6423, "lng": 139.7135, "demand": 2, "serviceTimeSec": 240, "window": { "startSec": 37800, "endSec": 45000 } }
  ],
  "vehicles": [
    { "id": 1, "name": "Electric Van Alpha", "capacity": 15, "maxShiftSec": 28800, "depotId": 0, "color": "#1A3A5B" },
    { "id": 2, "name": "Electric Van Beta", "capacity": 15, "maxShiftSec": 28800, "depotId": 0, "color": "#234E3E" }
  ]
}`;
