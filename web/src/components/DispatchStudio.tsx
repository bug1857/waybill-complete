import React, { useState } from 'react';
import {
  Play,
  RotateCcw,
  CheckCircle2,
  AlertOctagon,
  Clock,
  Package,
  Truck,
  ShieldCheck,
  MapPin,
  Maximize2,
  Navigation,
  Info,
  Calendar,
} from 'lucide-react';
import { formatObjective } from '../lib/format';
import { Instance, Route, SolveReport, Stop, Vehicle } from '../types';
import { formatSeconds } from '../core/eval/feasibility';
import { solveNearestNeighbour } from '../core/construct/nearestNeighbour';
import { solveClarkeWrightSavings } from '../core/construct/clarkeWright';
import { solveSimulatedAnnealing } from '../core/meta/simulatedAnnealing';
import { solveBranchAndBound } from '../core/exact/branchAndBound';

interface DispatchStudioProps {
  instance: Instance;
  setInstance: (inst: Instance) => void;
  report: SolveReport | null;
  setReport: (report: SolveReport) => void;
  onOpenReportModal: () => void;
}

export const DispatchStudio: React.FC<DispatchStudioProps> = ({
  instance,
  setInstance,
  report,
  setReport,
  onOpenReportModal,
}) => {
  const [selectedVehicleId, setSelectedVehicleId] = useState<number | 'ALL'>('ALL');
  const [selectedStopId, setSelectedStopId] = useState<number | null>(null);
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<
    'CLARKE_WRIGHT' | 'NEAREST_NEIGHBOUR' | 'SIMULATED_ANNEALING' | 'BRANCH_BOUND'
  >('CLARKE_WRIGHT');
  const [isRunning, setIsRunning] = useState(false);
  const [showTimeWindows, setShowTimeWindows] = useState(true);

  // Compute bounding box for responsive SVG map
  const minX = Math.min(...instance.stops.map((s) => s.x)) - 30;
  const maxX = Math.max(...instance.stops.map((s) => s.x)) + 30;
  const minY = Math.min(...instance.stops.map((s) => s.y)) - 30;
  const maxY = Math.max(...instance.stops.map((s) => s.y)) + 30;
  const width = Math.max(500, maxX - minX);
  const height = Math.max(400, maxY - minY);

  const handleSolve = () => {
    setIsRunning(true);
    setTimeout(() => {
      let result: SolveReport;
      if (selectedAlgorithm === 'CLARKE_WRIGHT') {
        result = solveClarkeWrightSavings(instance);
      } else if (selectedAlgorithm === 'NEAREST_NEIGHBOUR') {
        result = solveNearestNeighbour(instance);
      } else if (selectedAlgorithm === 'SIMULATED_ANNEALING') {
        result = solveSimulatedAnnealing(instance, { maxIterations: 3000, timeoutMs: 4000 });
      } else {
        result = solveBranchAndBound(instance, { boundType: 'ONE_TREE', timeoutMs: 4000 });
      }
      setReport(result);
      setIsRunning(false);
    }, 50);
  };

  const activeRoutes =
    selectedVehicleId === 'ALL'
      ? report?.routes ?? []
      : (report?.routes ?? []).filter((r) => r.vehicleId === selectedVehicleId);

  const selectedStop =
    selectedStopId !== null ? instance.stops.find((s) => s.id === selectedStopId) : null;

  return (
    <div className="space-y-6">
      {/* Top Banner / Summary */}
      <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-6 shadow-[3px_3px_0px_0px_#1A1A1A]">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold uppercase tracking-widest px-2.5 py-0.5 bg-[#1A1A1A] text-[#F7F3F0]">
                {instance.type} Formulation
              </span>
              <span className="text-xs text-[#66615C] font-mono">
                {instance.stops.length} Stops · {instance.vehicles.length} Fleet Vans
              </span>
              <span className="text-xs text-[#66615C] font-mono">
                Hash: {instance.distanceMatrix.hash}
              </span>
            </div>
            <h1 className="font-serif text-2xl sm:text-3xl font-semibold italic text-[#1A1A1A] mt-2">
              {instance.name}
            </h1>
            <p className="text-xs text-[#66615C] font-sans mt-1 max-w-3xl leading-relaxed">
              {instance.description}
            </p>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center bg-[#EBE7E4] p-1 border border-[#1A1A1A]">
              <select
                id="algo-select"
                value={selectedAlgorithm}
                onChange={(e) => setSelectedAlgorithm(e.target.value as any)}
                className="bg-transparent text-xs text-[#1A1A1A] font-mono py-1.5 px-3 focus:outline-none cursor-pointer"
              >
                <option value="CLARKE_WRIGHT" className="bg-[#FAF7F5] text-[#1A1A1A]">
                  Clarke–Wright Savings (Fleet Aware)
                </option>
                <option value="SIMULATED_ANNEALING" className="bg-[#FAF7F5] text-[#1A1A1A]">
                  Simulated Annealing (Anytime Metaheuristic)
                </option>
                <option value="NEAREST_NEIGHBOUR" className="bg-[#FAF7F5] text-[#1A1A1A]">
                  Nearest Neighbour (Greedy Baseline)
                </option>
                <option value="BRANCH_BOUND" className="bg-[#FAF7F5] text-[#1A1A1A]">
                  Branch &amp; Bound (1-Tree Exact Solver)
                </option>
              </select>

              <button
                id="btn-run-solve"
                onClick={handleSolve}
                disabled={isRunning}
                className="flex items-center gap-1.5 bg-[#1A1A1A] hover:bg-[#333333] active:bg-[#000000] text-[#F7F3F0] text-xs font-mono font-bold uppercase tracking-wider px-4 py-1.5 border border-[#1A1A1A] transition-all disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{isRunning ? 'Solving...' : 'Dispatch Fleet'}</span>
              </button>
            </div>

            {report && (
              <button
                id="btn-view-report"
                onClick={onOpenReportModal}
                className="flex items-center gap-1.5 bg-[#FAF7F5] hover:bg-[#EBE7E4] text-[#1A1A1A] text-xs font-mono font-semibold px-3 py-2 border border-[#1A1A1A] shadow-[2px_2px_0px_0px_#1A1A1A] transition"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-[#1A1A1A]" />
                <span>Inspect SolveReport</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Grid: Map & Route Details */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Interactive Map & Live Canvas (8 Cols) */}
        <div className="lg:col-span-8 space-y-4">
          <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] shadow-[3px_3px_0px_0px_#1A1A1A] flex flex-col">
            {/* Map Header Toolbar */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#1A1A1A] bg-[#EBE7E4]">
              <div className="flex items-center gap-2">
                <Navigation className="w-4 h-4 text-[#1A1A1A]" />
                <span className="text-xs font-mono font-bold text-[#1A1A1A] uppercase tracking-wider">
                  Route Graph ({instance.distanceMatrix.provider})
                </span>
              </div>

              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1.5 text-xs text-[#1A1A1A] font-mono cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showTimeWindows}
                    onChange={(e) => setShowTimeWindows(e.target.checked)}
                    className="rounded-none bg-[#FAF7F5] border-[#1A1A1A] text-[#1A1A1A] focus:ring-0 w-3.5 h-3.5 cursor-pointer"
                  />
                  <span>Time Windows</span>
                </label>

                {/* Filter vehicle */}
                <div className="flex items-center gap-1 text-xs font-mono">
                  <span className="text-[#66615C]">Filter:</span>
                  <button
                    id="filter-all-vans"
                    onClick={() => setSelectedVehicleId('ALL')}
                    className={`px-2 py-0.5 border text-xs transition ${
                      selectedVehicleId === 'ALL'
                        ? 'bg-[#1A1A1A] text-[#F7F3F0] border-[#1A1A1A] font-bold'
                        : 'bg-[#FAF7F5] text-[#1A1A1A] border-[#1A1A1A]/40 hover:border-[#1A1A1A]'
                    }`}
                  >
                    All Vans
                  </button>
                  {instance.vehicles.map((v) => (
                    <button
                      key={v.id}
                      id={`filter-van-${v.id}`}
                      onClick={() => setSelectedVehicleId(v.id)}
                      className={`px-2 py-0.5 border text-xs font-bold transition ${
                        selectedVehicleId === v.id
                          ? 'text-white border-[#1A1A1A]'
                          : 'text-[#1A1A1A] border-[#1A1A1A]/40 hover:border-[#1A1A1A] bg-[#FAF7F5]'
                      }`}
                      style={{
                        backgroundColor: selectedVehicleId === v.id ? v.color : undefined,
                      }}
                    >
                      {v.name.split(' ')[0]}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* SVG Visual Stage */}
            <div className="relative bg-[#FAF7F5] p-4 flex items-center justify-center min-h-[460px] overflow-auto">
              <svg
                viewBox={`${minX} ${minY} ${width} ${height}`}
                className="w-full h-full max-h-[550px] select-none"
              >
                <defs>
                  {/* Subtle architectural grid pattern */}
                  <pattern
                    id="mapGrid"
                    width="40"
                    height="40"
                    patternUnits="userSpaceOnUse"
                  >
                    <path
                      d="M 40 0 L 0 0 0 40"
                      fill="none"
                      stroke="#1A1A1A"
                      strokeOpacity="0.07"
                      strokeWidth="0.8"
                      strokeDasharray="2,2"
                    />
                  </pattern>

                  {/* Marker arrows for vehicles */}
                  {instance.vehicles.map((v) => (
                    <marker
                      key={`arrow-${v.id}`}
                      id={`arrow-${v.id}`}
                      viewBox="0 0 10 10"
                      refX="6"
                      refY="5"
                      markerWidth="6"
                      markerHeight="6"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 1 L 8 5 L 0 9 z" fill={v.color} opacity="0.9" />
                    </marker>
                  ))}
                </defs>

                {/* Grid Background */}
                <rect
                  x={minX}
                  y={minY}
                  width={width}
                  height={height}
                  fill="url(#mapGrid)"
                />

                {/* Route Polylines */}
                {activeRoutes.map((r, rIdx) => {
                  const vehicle =
                    instance.vehicles.find((v) => v.id === r.vehicleId) ||
                    instance.vehicles[0];
                  const points = r.stopIds
                    .map((id) => {
                      const stop = instance.stops.find((s) => s.id === id);
                      return stop ? `${stop.x},${stop.y}` : '';
                    })
                    .filter(Boolean)
                    .join(' ');

                  return (
                    <g key={`route-${r.vehicleId}-${rIdx}`}>
                      {/* Outline */}
                      <polyline
                        points={points}
                        fill="none"
                        stroke={vehicle.color}
                        strokeWidth="6"
                        strokeOpacity="0.25"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                      />
                      {/* Active line */}
                      <polyline
                        points={points}
                        fill="none"
                        stroke={vehicle.color}
                        strokeWidth="2.4"
                        strokeOpacity="0.95"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                        markerMid={`url(#arrow-${vehicle.id})`}
                      />
                    </g>
                  );
                })}

                {/* Stops Rendering */}
                {instance.stops.map((stop) => {
                  const isSelected = selectedStopId === stop.id;
                  const isDepot = stop.isDepot;

                  // Find which vehicle visits this stop
                  let visitingVehicle: Vehicle | undefined;
                  let sequenceNumber = -1;

                  if (report) {
                    for (const r of report.routes) {
                      const idx = r.stopIds.indexOf(stop.id);
                      if (idx > 0 && idx < r.stopIds.length - 1) {
                        visitingVehicle = instance.vehicles.find((v) => v.id === r.vehicleId);
                        sequenceNumber = idx;
                        break;
                      }
                    }
                  }

                  const fillColor = isDepot
                    ? '#1A1A1A'
                    : visitingVehicle
                    ? visitingVehicle.color
                    : '#66615C';

                  return (
                    <g
                      key={`stop-${stop.id}`}
                      onClick={() => setSelectedStopId(stop.id)}
                      className="cursor-pointer transition-transform hover:scale-110"
                      transform={`translate(${stop.x}, ${stop.y})`}
                    >
                      {/* Selection Halo */}
                      {isSelected && (
                        <circle
                          r="16"
                          fill="none"
                          stroke="#1A1A1A"
                          strokeWidth="2.5"
                          strokeDasharray="3,3"
                        />
                      )}

                      {/* Stop Node */}
                      {isDepot ? (
                        <rect
                          x="-10"
                          y="-10"
                          width="20"
                          height="20"
                          fill="#1A1A1A"
                          stroke="#FAF7F5"
                          strokeWidth="2"
                        />
                      ) : (
                        <circle
                          r="8"
                          fill={fillColor}
                          stroke="#FAF7F5"
                          strokeWidth="1.5"
                        />
                      )}

                      {/* Stop ID / Sequence Number */}
                      <text
                        textAnchor="middle"
                        dy="3"
                        fill="#FAF7F5"
                        fontSize="9"
                        fontWeight="bold"
                        className="pointer-events-none font-mono"
                      >
                        {isDepot ? 'D' : sequenceNumber > 0 ? sequenceNumber : stop.id}
                      </text>

                      {/* Demand Badge */}
                      {!isDepot && stop.demand > 0 && (
                        <g transform="translate(8, -8)">
                          <circle r="5.5" fill="#FAF7F5" stroke="#1A1A1A" strokeWidth="1" />
                          <text
                            textAnchor="middle"
                            dy="2.5"
                            fill="#1A1A1A"
                            fontSize="7.5"
                            fontWeight="bold"
                            className="font-mono"
                          >
                            {stop.demand}p
                          </text>
                        </g>
                      )}

                      {/* Time window indicator pill */}
                      {showTimeWindows && stop.window && (
                        <g transform="translate(0, 15)">
                          <rect
                            x="-22"
                            y="-6"
                            width="44"
                            height="11"
                            fill="#EBE7E4"
                            stroke="#1A1A1A"
                            strokeWidth="0.8"
                            opacity="0.95"
                          />
                          <text
                            textAnchor="middle"
                            dy="2.5"
                            fill="#1A1A1A"
                            fontSize="6.5"
                            fontWeight="600"
                            className="font-mono"
                          >
                            {formatSeconds(stop.window.startSec).slice(0, 5)}
                          </text>
                        </g>
                      )}
                    </g>
                  );
                })}
              </svg>

              {/* Map Overlay Badge */}
              <div className="absolute bottom-3 left-3 bg-[#FAF7F5] border border-[#1A1A1A] px-3 py-1.5 text-xs font-mono text-[#1A1A1A] shadow-[2px_2px_0px_0px_#1A1A1A]">
                <span className="text-[#66615C]">Stops:</span> {instance.stops.length} |{' '}
                <span className="text-[#66615C]">Fleet:</span> {instance.vehicles.length} vans |{' '}
                <span className="text-[#66615C]">Units:</span> {instance.distanceMatrix.units}
              </div>
            </div>

            {/* Bottom Status Bar: Feasibility Gate Audit */}
            {report && (
              <div
                className={`p-3.5 border-t-2 border-[#1A1A1A] text-xs font-mono flex flex-wrap items-center justify-between gap-2 ${
                  report.feasibilityAudit.passed
                    ? 'bg-[#234E3E]/10 text-[#234E3E]'
                    : 'bg-[#B84A39]/10 text-[#B84A39]'
                }`}
              >
                <div className="flex items-center gap-2">
                  {report.feasibilityAudit.passed ? (
                    <CheckCircle2 className="w-4 h-4 text-[#234E3E]" />
                  ) : (
                    <AlertOctagon className="w-4 h-4 text-[#B84A39]" />
                  )}
                  <span className="font-bold uppercase tracking-wider">
                    Feasibility Gate:{' '}
                    {report.feasibilityAudit.passed
                      ? '100% Passed (All Constraints Satisfied)'
                      : `${report.feasibilityAudit.violations.length} Violations Found`}
                  </span>
                </div>

                <div className="flex items-center gap-4 text-xs font-mono text-[#1A1A1A]">
                  <span>
                    Total Distance:{' '}
                    <strong>
                      {formatObjective(report.objective_value, instance.distanceMatrix.units)}
                    </strong>
                  </span>
                  <span>
                    Compute Time:{' '}
                    <strong>{report.wall_time_ms} ms</strong>
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Stop Inspector Card */}
          {selectedStop && (
            <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-4 shadow-[3px_3px_0px_0px_#1A1A1A]">
              <div className="flex items-center justify-between pb-3 border-b border-[#1A1A1A]">
                <div className="flex items-center gap-2.5">
                  <div className="h-7 w-7 bg-[#1A1A1A] text-[#F7F3F0] flex items-center justify-center font-mono font-bold text-xs">
                    #{selectedStop.id}
                  </div>
                  <div>
                    <h2 className="font-serif text-lg font-semibold italic text-[#1A1A1A]">{selectedStop.name}</h2>
                    <p className="text-xs text-[#66615C] font-mono">
                      Coordinates: ({selectedStop.x}, {selectedStop.y}){' '}
                      {selectedStop.lat && `· GPS: ${selectedStop.lat.toFixed(4)}, ${selectedStop.lng?.toFixed(4)}`}
                    </p>
                  </div>
                </div>
                <span className="text-xs font-mono px-2.5 py-0.5 bg-[#EBE7E4] border border-[#1A1A1A] text-[#1A1A1A] font-semibold">
                  {selectedStop.isDepot ? 'Distribution Depot' : `Parcel Demand: ${selectedStop.demand} pkgs`}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3 text-xs font-mono">
                <div className="bg-[#EBE7E4] p-2.5 border border-[#1A1A1A]/40">
                  <div className="text-[#66615C]">Time Window</div>
                  <div className="text-[#1A1A1A] font-bold mt-0.5">
                    {selectedStop.window
                      ? `${formatSeconds(selectedStop.window.startSec)} – ${formatSeconds(selectedStop.window.endSec)}`
                      : 'None (Unconstrained)'}
                  </div>
                </div>

                <div className="bg-[#EBE7E4] p-2.5 border border-[#1A1A1A]/40">
                  <div className="text-[#66615C]">Service Duration</div>
                  <div className="text-[#1A1A1A] font-bold mt-0.5">
                    {Math.round(selectedStop.serviceTimeSec / 60)} mins at door
                  </div>
                </div>

                <div className="bg-[#EBE7E4] p-2.5 border border-[#1A1A1A]/40">
                  <div className="text-[#66615C]">Demand / Capacity</div>
                  <div className="text-[#1A1A1A] font-bold mt-0.5">
                    {selectedStop.demand} parcels
                  </div>
                </div>

                <div className="bg-[#EBE7E4] p-2.5 border border-[#1A1A1A]/40">
                  <div className="text-[#66615C]">Visit Status</div>
                  <div className="text-[#234E3E] font-bold mt-0.5">
                    {report?.routes.some((r) => r.stopIds.includes(selectedStop.id))
                      ? 'Scheduled & Assigned'
                      : 'Unassigned'}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Fleet Utilization & Stop ETA Timeline (4 Cols) */}
        <div className="lg:col-span-4 space-y-4">
          {/* Fleet Vehicle Cards */}
          <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-4 shadow-[3px_3px_0px_0px_#1A1A1A] space-y-3">
            <div className="flex items-center justify-between border-b border-[#1A1A1A] pb-2">
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-[#1A1A1A] flex items-center gap-1.5">
                <Truck className="w-3.5 h-3.5 text-[#1A1A1A]" />
                <span>Vehicle Fleet Utilization</span>
              </h2>
              <span className="text-xs font-mono text-[#66615C]">
                {instance.vehicles.length} Vehicles
              </span>
            </div>

            <div className="space-y-2.5 max-h-[280px] overflow-y-auto pr-1">
              {instance.vehicles.map((vehicle) => {
                const assignedRoute = report?.routes.find((r) => r.vehicleId === vehicle.id);
                const stopCount = assignedRoute ? assignedRoute.stopIds.length - 2 : 0;
                const load = assignedRoute ? assignedRoute.totalDemand : 0;
                // A TSP salesman is modelled as an unconstrained vehicle, so its
                // capacity and shift are sentinels rather than real limits. Render
                // them as unlimited rather than printing MAX_SAFE_INTEGER.
                const UNBOUNDED = Number.MAX_SAFE_INTEGER / 2;
                const capUnbounded = vehicle.capacity >= UNBOUNDED;
                const shiftUnbounded = vehicle.maxShiftSec >= UNBOUNDED;
                const capacityPct = capUnbounded
                  ? 0
                  : Math.min(100, Math.round((load / vehicle.capacity) * 100));
                const durationHrs = assignedRoute ? (assignedRoute.durationSec / 3600).toFixed(1) : '0.0';
                const maxShiftHrs = shiftUnbounded ? '∞' : (vehicle.maxShiftSec / 3600).toFixed(0);

                return (
                  <div
                    key={vehicle.id}
                    onClick={() => setSelectedVehicleId(vehicle.id)}
                    className={`p-3 border transition-all cursor-pointer ${
                      selectedVehicleId === vehicle.id
                        ? 'bg-[#EBE7E4] border-[#1A1A1A] shadow-[2px_2px_0px_0px_#1A1A1A]'
                        : 'bg-[#FAF7F5] border-[#1A1A1A]/30 hover:border-[#1A1A1A] hover:bg-[#EBE7E4]/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-3 h-3 border border-[#1A1A1A]"
                          style={{ backgroundColor: vehicle.color }}
                        />
                        <span className="text-xs font-bold text-[#1A1A1A]">
                          {vehicle.name}
                        </span>
                      </div>
                      <span className="text-xs font-mono text-[#66615C]">
                        {stopCount} stops
                      </span>
                    </div>

                    {/* Capacity Bar */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px] font-mono text-[#66615C]">
                        <span>Parcel Load:</span>
                        <span className={load > vehicle.capacity ? 'text-[#B84A39] font-bold' : 'text-[#1A1A1A] font-semibold'}>
                          {capUnbounded
                            ? `${load} pkgs (no capacity limit)`
                            : `${load} / ${vehicle.capacity} pkgs (${capacityPct}%)`}
                        </span>
                      </div>
                      <div className="w-full bg-[#EBE7E4] border border-[#1A1A1A]/30 h-2 overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${
                            load > vehicle.capacity
                              ? 'bg-[#B84A39]'
                              : capacityPct > 85
                              ? 'bg-[#C27803]'
                              : 'bg-[#234E3E]'
                          }`}
                          style={{ width: `${capacityPct}%` }}
                        />
                      </div>
                    </div>

                    {/* Shift Duration */}
                    <div className="flex justify-between items-center mt-2 text-[11px] font-mono text-[#66615C]">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-[#1A1A1A]" /> Shift Time:
                      </span>
                      <span className="text-[#1A1A1A] font-semibold">
                        {durationHrs}h / {maxShiftHrs}h
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Chronological Stop ETA Audit Timeline */}
          <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-4 shadow-[3px_3px_0px_0px_#1A1A1A] space-y-3">
            <div className="flex items-center justify-between border-b border-[#1A1A1A] pb-2">
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-[#1A1A1A] flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-[#1A1A1A]" />
                <span>Stop ETA Timeline</span>
              </h2>
              <span className="text-xs font-mono text-[#66615C]">
                {selectedVehicleId === 'ALL' ? 'Vehicle 1' : `Van ${selectedVehicleId}`}
              </span>
            </div>

            {report && report.routes.length > 0 ? (
              <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
                {(() => {
                  const targetRoute =
                    selectedVehicleId === 'ALL'
                      ? report.routes[0]
                      : report.routes.find((r) => r.vehicleId === selectedVehicleId) ||
                        report.routes[0];

                  if (!targetRoute || targetRoute.stopAudits.length === 0) {
                    return (
                      <p className="text-xs text-[#66615C] font-mono py-4 text-center">
                        No stops assigned to this vehicle route.
                      </p>
                    );
                  }

                  return targetRoute.stopAudits.map((audit, idx) => (
                    <div
                      key={`audit-${idx}`}
                      onClick={() => setSelectedStopId(audit.stopId)}
                      className={`p-2.5 border text-xs font-mono transition cursor-pointer ${
                        audit.windowViolation
                          ? 'bg-[#B84A39]/10 border-[#B84A39] text-[#B84A39]'
                          : selectedStopId === audit.stopId
                          ? 'bg-[#EBE7E4] border-[#1A1A1A] text-[#1A1A1A] shadow-[2px_2px_0px_0px_#1A1A1A]'
                          : 'bg-[#FAF7F5] border-[#1A1A1A]/30 hover:border-[#1A1A1A] text-[#1A1A1A]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <span className="w-5 h-5 bg-[#1A1A1A] text-[#F7F3F0] flex items-center justify-center font-bold text-[10px]">
                            {idx === 0 ? 'D' : idx}
                          </span>
                          <span className="font-semibold text-[#1A1A1A] truncate max-w-[140px]">
                            {audit.name}
                          </span>
                        </div>
                        <span className="text-[#1A1A1A] font-bold">
                          {formatSeconds(audit.arrivalSec)}
                        </span>
                      </div>

                      <div className="flex justify-between items-center text-[10px] text-[#66615C] mt-1.5 pt-1 border-t border-[#1A1A1A]/20">
                        <span>Leg: {(audit.distanceFromPrevMetres / 1000).toFixed(1)} km</span>
                        <span>Load: {audit.cumulativeLoad} pkgs</span>
                        {audit.waitingSec > 0 && (
                          <span className="text-[#C27803] font-bold">
                            Wait: {Math.round(audit.waitingSec / 60)}m
                          </span>
                        )}
                      </div>
                    </div>
                  ));
                })()}
              </div>
            ) : (
              <div className="text-center py-8 text-xs font-mono text-[#66615C]">
                Click <strong>"Dispatch Fleet"</strong> to calculate multi-vehicle routes and generate the live ETA audit timeline.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
