import React, { useState } from 'react';
import {
  Play,
  Binary,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Cpu,
  Flame,
  ShieldCheck,
  Award,
  GitCommit,
  Maximize,
  ArrowRight,
  TrendingDown,
} from 'lucide-react';
import {
  BranchBoundNodeInfo,
  Instance,
  SolveReport,
  SolveStatus,
  SolveTracePoint,
} from '../types';
import { formatObjective } from '../lib/format';
import { solveBruteForce } from '../core/exact/bruteForce';
import { solveHeldKarp } from '../core/exact/heldKarp';
import {
  BoundType,
  SearchStrategy,
  solveBranchAndBound,
} from '../core/exact/branchAndBound';
import { solveNearestNeighbour } from '../core/construct/nearestNeighbour';
import { solveClarkeWrightSavings } from '../core/construct/clarkeWright';
import { improveOrOpt } from '../core/local/orOpt';
import { improveTwoOpt } from '../core/local/twoOpt';
import { solveSimulatedAnnealing } from '../core/meta/simulatedAnnealing';
import { checkInstanceFeasibility } from '../core/eval/feasibility';

interface SolverSandboxProps {
  instance: Instance;
  report: SolveReport | null;
  setReport: (report: SolveReport) => void;
  onOpenReportModal: () => void;
}

export const SolverSandbox: React.FC<SolverSandboxProps> = ({
  instance,
  report,
  setReport,
  onOpenReportModal,
}) => {
  const [selectedSolver, setSelectedSolver] = useState<
    | 'BRUTE_FORCE'
    | 'HELD_KARP'
    | 'BB_ONE_TREE'
    | 'BB_HUNGARIAN'
    | 'BB_REDUCED_COST'
    | 'NEAREST_NEIGHBOUR'
    | 'CLARKE_WRIGHT'
    | 'OR_OPT'
    | 'TWO_OPT'
    | 'SIMULATED_ANNEALING'
  >('BB_ONE_TREE');

  const [bbStrategy, setBbStrategy] = useState<SearchStrategy>('BEST_FIRST');
  const [timeoutSec, setTimeoutSec] = useState<number>(5);
  const [saTemp, setSaTemp] = useState<number>(500);
  const [saCooling, setSaCooling] = useState<number>(0.997);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedTreeNode, setSelectedTreeNode] = useState<BranchBoundNodeInfo | null>(null);

  const handleRun = () => {
    setIsRunning(true);

    setTimeout(() => {
      let result: SolveReport;
      const timeoutMs = timeoutSec * 1000;

      if (selectedSolver === 'BRUTE_FORCE') {
        result = solveBruteForce(instance, { timeoutMs });
      } else if (selectedSolver === 'HELD_KARP') {
        result = solveHeldKarp(instance, { timeoutMs });
      } else if (selectedSolver === 'BB_ONE_TREE') {
        result = solveBranchAndBound(instance, {
          boundType: 'ONE_TREE',
          strategy: bbStrategy,
          timeoutMs,
        });
      } else if (selectedSolver === 'BB_HUNGARIAN') {
        result = solveBranchAndBound(instance, {
          boundType: 'HUNGARIAN',
          strategy: bbStrategy,
          timeoutMs,
        });
      } else if (selectedSolver === 'BB_REDUCED_COST') {
        result = solveBranchAndBound(instance, {
          boundType: 'REDUCED_COST',
          strategy: bbStrategy,
          timeoutMs,
        });
      } else if (selectedSolver === 'NEAREST_NEIGHBOUR') {
        result = solveNearestNeighbour(instance);
      } else if (selectedSolver === 'CLARKE_WRIGHT') {
        result = solveClarkeWrightSavings(instance);
      } else if (selectedSolver === 'OR_OPT') {
        const seedRep = solveNearestNeighbour(instance);
        const seedTour = seedRep.routes[0]?.stopIds ?? [0, 1, 0];
        const res = improveOrOpt(seedTour, instance.distanceMatrix.matrix);
        const audit = checkInstanceFeasibility(instance, [
          { vehicleId: 1, stopIds: res.tour },
        ]);
        result = {
          ...seedRep,
          solver_name: 'Or-Opt / Relocate (Asymmetry Safe)',
          objective_value: res.cost,
          routes: audit.auditedRoutes,
          feasibilityAudit: {
            passed: audit.passed,
            allCustomersVisitedOnce: audit.allCustomersVisitedOnce,
            capacityRespected: audit.capacityRespected,
            timeWindowsRespected: audit.timeWindowsRespected,
            shiftDurationRespected: audit.shiftDurationRespected,
            violations: audit.violations,
          },
        };
      } else if (selectedSolver === 'TWO_OPT') {
        const seedRep = solveNearestNeighbour(instance);
        const seedTour = seedRep.routes[0]?.stopIds ?? [0, 1, 0];
        const res = improveTwoOpt(
          seedTour,
          instance.distanceMatrix.matrix,
          instance.distanceMatrix.isSymmetric
        );
        const audit = checkInstanceFeasibility(instance, [
          { vehicleId: 1, stopIds: res.tour },
        ]);
        result = {
          ...seedRep,
          solver_name: `2-Opt (${res.evaluationComplexity})`,
          objective_value: res.cost,
          routes: audit.auditedRoutes,
          feasibilityAudit: {
            passed: audit.passed,
            allCustomersVisitedOnce: audit.allCustomersVisitedOnce,
            capacityRespected: audit.capacityRespected,
            timeWindowsRespected: audit.timeWindowsRespected,
            shiftDurationRespected: audit.shiftDurationRespected,
            violations: audit.violations,
          },
        };
      } else {
        result = solveSimulatedAnnealing(instance, {
          initialTemp: saTemp,
          coolingRate: saCooling,
          timeoutMs,
        });
      }

      setReport(result);
      setIsRunning(false);
    }, 40);
  };

  const isBB = selectedSolver.startsWith('BB_');
  const isSA = selectedSolver === 'SIMULATED_ANNEALING';

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-6 shadow-[3px_3px_0px_0px_#1A1A1A]">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold uppercase tracking-widest px-2.5 py-0.5 bg-[#1A1A1A] text-[#F7F3F0]">
                DAA Rigorous Solver Suite
              </span>
              <span className="text-xs text-[#66615C] font-mono">
                Instance: {instance.name} ({instance.stops.length} stops)
              </span>
            </div>
            <h1 className="font-serif text-2xl sm:text-3xl font-semibold italic text-[#1A1A1A] mt-2">
              Algorithm Execution &amp; Formal Optimality Prover
            </h1>
            <p className="text-xs text-[#66615C] font-sans mt-1 max-w-3xl leading-relaxed">
              Run exact algorithms (Branch &amp; Bound, Held–Karp, Brute Force) or scalable heuristics with complete instrumentation.
            </p>
          </div>

          {/* Solver Controls */}
          <div className="flex flex-wrap items-center gap-3">
            <select
              id="solver-dropdown"
              value={selectedSolver}
              onChange={(e) => setSelectedSolver(e.target.value as any)}
              className="bg-[#FAF7F5] text-[#1A1A1A] border border-[#1A1A1A] text-xs font-mono py-2 px-3 focus:outline-none cursor-pointer shadow-[1px_1px_0px_0px_#1A1A1A]"
            >
              <optgroup label="1. Exact Solvers (Provable Optimality)">
                <option value="BB_ONE_TREE">B&amp;B + 1-Tree Subgradient (Recommended)</option>
                <option value="BB_HUNGARIAN">B&amp;B + Hungarian LAP Bound (Mandatory)</option>
                <option value="BB_REDUCED_COST">B&amp;B + Reduced Cost Matrix (Mandatory)</option>
                <option value="HELD_KARP">Held–Karp Dynamic Programming (Memory Wall)</option>
                <option value="BRUTE_FORCE">Brute Force Enumeration (n ≤ 12 Truth)</option>
              </optgroup>
              <optgroup label="2. Constructive &amp; Local Heuristics">
                <option value="CLARKE_WRIGHT">Clarke–Wright Savings (Fleet Aware)</option>
                <option value="NEAREST_NEIGHBOUR">Nearest Neighbour (Greedy Baseline)</option>
                <option value="OR_OPT">Or-Opt Relocate (Asymmetry-Safe O(1))</option>
                <option value="TWO_OPT">2-Opt (with Strict Symmetry Guard)</option>
              </optgroup>
              <optgroup label="3. Metaheuristic (Anytime)">
                <option value="SIMULATED_ANNEALING">Simulated Annealing (Anytime Curve)</option>
              </optgroup>
            </select>

            <button
              id="btn-execute-solver"
              onClick={handleRun}
              disabled={isRunning}
              className="flex items-center gap-1.5 bg-[#1A1A1A] hover:bg-[#333333] active:bg-[#000000] text-[#F7F3F0] text-xs font-mono font-bold uppercase tracking-wider px-5 py-2 border border-[#1A1A1A] transition disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{isRunning ? 'Computing Proof...' : 'Execute Solver'}</span>
            </button>
          </div>
        </div>

        {/* Algorithm Specific Parameter Dials */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4 pt-4 border-t border-[#1A1A1A]/20 text-xs font-mono">
          <div className="bg-[#EBE7E4] p-3 border border-[#1A1A1A]/40">
            <label className="text-[#66615C] block mb-1 font-semibold uppercase tracking-wider text-[10px]">Time Budget</label>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min="1"
                max="20"
                value={timeoutSec}
                onChange={(e) => setTimeoutSec(Number(e.target.value))}
                className="w-full accent-[#1A1A1A]"
              />
              <span className="text-[#1A1A1A] font-bold w-12 text-right">{timeoutSec}s</span>
            </div>
          </div>

          {isBB && (
            <div className="bg-[#EBE7E4] p-3 border border-[#1A1A1A]/40">
              <label className="text-[#66615C] block mb-1 font-semibold uppercase tracking-wider text-[10px]">Search Strategy</label>
              <select
                value={bbStrategy}
                onChange={(e) => setBbStrategy(e.target.value as any)}
                className="w-full bg-[#FAF7F5] text-[#1A1A1A] py-1 px-2 border border-[#1A1A1A] focus:outline-none"
              >
                <option value="BEST_FIRST">Best-First Search (Priority Queue by LB)</option>
                <option value="DEPTH_FIRST">Depth-First Search (DFS with Pruning)</option>
              </select>
            </div>
          )}

          {isSA && (
            <>
              <div className="bg-[#EBE7E4] p-3 border border-[#1A1A1A]/40">
                <label className="text-[#66615C] block mb-1 font-semibold uppercase tracking-wider text-[10px]">Initial Temperature (T₀)</label>
                <input
                  type="number"
                  value={saTemp}
                  onChange={(e) => setSaTemp(Number(e.target.value))}
                  className="w-full bg-[#FAF7F5] text-[#1A1A1A] py-1 px-2 border border-[#1A1A1A] font-mono"
                />
              </div>

              <div className="bg-[#EBE7E4] p-3 border border-[#1A1A1A]/40">
                <label className="text-[#66615C] block mb-1 font-semibold uppercase tracking-wider text-[10px]">Cooling Rate (α)</label>
                <input
                  type="number"
                  step="0.001"
                  value={saCooling}
                  onChange={(e) => setSaCooling(Number(e.target.value))}
                  className="w-full bg-[#FAF7F5] text-[#1A1A1A] py-1 px-2 border border-[#1A1A1A] font-mono"
                />
              </div>
            </>
          )}

          <div className="bg-[#EBE7E4] p-3 border border-[#1A1A1A]/40 flex items-center justify-between">
            <div>
              <div className="text-[#66615C] font-semibold uppercase tracking-wider text-[10px]">Distance Matrix Type</div>
              <div className="text-[#1A1A1A] font-bold mt-0.5">
                {instance.distanceMatrix.isSymmetric ? 'Symmetric Euclidean' : 'Asymmetric Real-Road'}
              </div>
            </div>
            <span className="text-[#66615C] text-[11px]">
              {instance.distanceMatrix.units}
            </span>
          </div>
        </div>
      </div>

      {/* Solver Execution Telemetry & Evidence */}
      {report && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Tile 1: Status & Claim Discipline */}
          <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-4 shadow-[2px_2px_0px_0px_#1A1A1A] space-y-2">
            <div className="text-[10px] font-mono font-bold text-[#66615C] uppercase tracking-wider">
              Claim Model Status (§02)
            </div>
            <div className="flex items-center gap-2">
              {report.status === SolveStatus.PROVEN_OPTIMAL_TSP ? (
                <CheckCircle2 className="w-5 h-5 text-[#234E3E] shrink-0" />
              ) : report.status === SolveStatus.HEURISTIC_FEASIBLE_CVRPTW ? (
                <ShieldCheck className="w-5 h-5 text-[#1A3A5B] shrink-0" />
              ) : (
                <Award className="w-5 h-5 text-[#C27803] shrink-0" />
              )}
              <span className="text-xs font-bold text-[#1A1A1A] font-mono leading-tight">
                {report.status}
              </span>
            </div>
            <p className="text-xs text-[#66615C] font-sans italic border-t border-[#1A1A1A]/20 pt-2">
              {report.permitted_wording}
            </p>
          </div>

          {/* Tile 2: Objective & Proven Gap */}
          <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-4 shadow-[2px_2px_0px_0px_#1A1A1A] space-y-2">
            <div className="text-[10px] font-mono font-bold text-[#66615C] uppercase tracking-wider">
              Objective &amp; Lower Bound
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-bold text-[#1A1A1A] font-mono">
                {formatObjective(report.objective_value, instance.distanceMatrix.units)}
                <span className="text-xs text-[#66615C] font-normal ml-1">km</span>
              </span>
              {report.best_lower_bound !== undefined && (
                <span className="text-xs font-mono text-[#66615C]">
                  LB: {formatObjective(report.best_lower_bound, instance.distanceMatrix.units)}
                </span>
              )}
            </div>
            <div className="text-xs font-mono text-[#66615C] border-t border-[#1A1A1A]/20 pt-2 flex justify-between">
              <span>Optimality Gap:</span>
              <strong className={report.proven_gap === 0 ? 'text-[#234E3E]' : 'text-[#C27803]'}>
                {report.proven_gap !== undefined ? `${(report.proven_gap * 100).toFixed(2)}% (Certified)` : 'N/A (Heuristic)'}
              </strong>
            </div>
          </div>

          {/* Tile 3: Search Complexity & Node Counts */}
          <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-4 shadow-[2px_2px_0px_0px_#1A1A1A] space-y-2">
            <div className="text-[10px] font-mono font-bold text-[#66615C] uppercase tracking-wider">
              Search Tree Complexity
            </div>
            <div className="text-2xl font-bold text-[#1A1A1A] font-mono">
              {report.nodes_explored?.toLocaleString() ?? 0}
              <span className="text-xs text-[#66615C] font-normal ml-1">nodes</span>
            </div>
            <div className="text-xs font-mono text-[#66615C] border-t border-[#1A1A1A]/20 pt-2 flex justify-between">
              <span>Pruned Subtrees:</span>
              <span className="text-[#1A1A1A] font-bold">
                {report.nodes_pruned?.toLocaleString() ?? 0}
              </span>
            </div>
          </div>

          {/* Tile 4: Wall Time & Compute Overhead */}
          <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-4 shadow-[2px_2px_0px_0px_#1A1A1A] space-y-2">
            <div className="text-[10px] font-mono font-bold text-[#66615C] uppercase tracking-wider">
              Runtime &amp; Isolation
            </div>
            <div className="text-2xl font-bold text-[#1A1A1A] font-mono">
              {report.wall_time_ms}
              <span className="text-xs text-[#66615C] font-normal ml-1">ms</span>
            </div>
            <div className="text-xs font-mono text-[#66615C] border-t border-[#1A1A1A]/20 pt-2 flex justify-between">
              <span>Bound Overhead:</span>
              <span className="text-[#1A1A1A] font-bold">
                {report.bound_time_ms !== undefined ? `${report.bound_time_ms} ms` : '0 ms'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Main Analysis Section: B&B Tree Viewer or Metaheuristic Convergence */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Interactive Tree Explorer or Incumbent Trace (7 Cols) */}
        <div className="lg:col-span-7 bg-[#FAF7F5] border-2 border-[#1A1A1A] p-5 shadow-[3px_3px_0px_0px_#1A1A1A] space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#1A1A1A]">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#1A1A1A]" />
              <h2 className="font-serif text-lg font-semibold italic text-[#1A1A1A]">
                {report?.bbTree ? 'Branch & Bound Search Tree Explorer' : 'Incumbent Progression & Convergence'}
              </h2>
            </div>
            <span className="text-xs font-mono text-[#66615C]">
              {report?.solver_name ?? 'No active run'}
            </span>
          </div>

          {/* B&B Tree Visualizer */}
          {report?.bbTree && report.bbTree.length > 0 ? (
            <div className="space-y-3">
              <p className="text-xs text-[#66615C]">
                Interactive Branch &amp; Bound search state hierarchy. Click any node to inspect lower bound calculation and pruning reason.
              </p>

              <div className="bg-[#EBE7E4] p-4 border border-[#1A1A1A]/40 max-h-[380px] overflow-y-auto space-y-2 font-mono text-xs">
                {report.bbTree.map((node) => (
                  <div
                    key={`tree-node-${node.id}`}
                    onClick={() => setSelectedTreeNode(node)}
                    className={`p-2.5 border transition cursor-pointer flex items-center justify-between ${
                      node.pruned
                        ? 'bg-[#B84A39]/10 border-[#B84A39] text-[#B84A39]'
                        : selectedTreeNode?.id === node.id
                        ? 'bg-[#FAF7F5] border-2 border-[#1A1A1A] text-[#1A1A1A] shadow-[2px_2px_0px_0px_#1A1A1A]'
                        : 'bg-[#FAF7F5] border-[#1A1A1A]/30 hover:border-[#1A1A1A] text-[#1A1A1A]'
                    }`}
                    style={{ marginLeft: `${Math.min(160, node.depth * 18)}px` }}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span className="text-[10px] bg-[#1A1A1A] text-[#F7F3F0] px-1.5 py-0.5 font-bold">
                        D{node.depth}
                      </span>
                      <span className="font-semibold text-[#1A1A1A]">
                        Path: [{node.partialTour.join('→')}]
                      </span>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-[#66615C]">
                        LB: <strong>{node.lowerBound}m</strong>
                      </span>
                      {node.pruned ? (
                        <span className="text-[10px] bg-[#B84A39] text-white px-1.5 py-0.5 font-bold">
                          PRUNED
                        </span>
                      ) : (
                        <span className="text-[10px] bg-[#234E3E] text-white px-1.5 py-0.5 font-bold">
                          BRANCHED
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : report?.trace && report.trace.length > 0 ? (
            <div className="space-y-3">
              <p className="text-xs text-[#66615C]">
                Optimization trace recorded against compute iterations and time.
              </p>
              <div className="bg-[#EBE7E4] p-3 border border-[#1A1A1A]/40 max-h-[380px] overflow-y-auto space-y-1.5 font-mono text-xs">
                {report.trace.map((pt, idx) => (
                  <div
                    key={`trace-${idx}`}
                    className="flex items-center justify-between p-2 bg-[#FAF7F5] border border-[#1A1A1A]/30 text-[#1A1A1A] text-[11px]"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-[#66615C]">#{pt.iteration}</span>
                      <span className="text-[#1A1A1A] font-semibold">{pt.action}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span>Cost: <strong className="text-[#B84A39]">{pt.cost}m</strong></span>
                      {pt.temperature !== undefined && (
                        <span className="text-[#C27803]">T: {pt.temperature}</span>
                      )}
                      <span className="text-[#66615C]">{pt.timeMs}ms</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-xs font-mono text-[#66615C]">
              Run a solver to explore the execution tree and convergence traces.
            </div>
          )}
        </div>

        {/* Right Column: Formal Proof Certificate & Node Inspector (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Certificate Card */}
          {report?.certificate ? (
            <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-5 shadow-[3px_3px_0px_0px_#1A1A1A] space-y-3">
              <div className="flex items-center gap-2 text-[#234E3E]">
                <ShieldCheck className="w-5 h-5" />
                <h3 className="font-serif text-base font-bold italic text-[#1A1A1A]">
                  Formal Optimality Certificate (§02)
                </h3>
              </div>

              <p className="text-xs text-[#1A1A1A] leading-relaxed">
                This TSP tour has been mathematically proven globally optimal via exhaustive search tree exhaustion with no unpruned subtrees remaining.
              </p>

              <div className="space-y-1.5 font-mono text-xs pt-2 border-t border-[#1A1A1A]/20 text-[#1A1A1A]">
                <div className="flex justify-between">
                  <span className="text-[#66615C]">Proof Technique:</span>
                  <span className="text-[#234E3E] font-bold">
                    {report.certificate.proofType}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#66615C]">Verified States:</span>
                  <span className="font-bold">{report.certificate.nodesVerified.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#66615C]">Optimal Cost:</span>
                  <span className="text-[#1A1A1A] font-bold">{report.objective_value} metres</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#66615C]">Timestamp:</span>
                  <span className="text-[#66615C]">{new Date(report.certificate.verifiedAt).toLocaleTimeString()}</span>
                </div>
              </div>

              <div className="p-2.5 bg-[#EBE7E4] border border-[#1A1A1A]/30 text-[11px] font-mono text-[#1A1A1A]">
                <div className="text-[#66615C] text-[10px] uppercase font-bold">Optimal Cycle:</div>
                <div className="text-[#1A1A1A] font-bold truncate">
                  {report.certificate.optimalTour.join(' → ')}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-5 shadow-[3px_3px_0px_0px_#1A1A1A] space-y-3">
              <div className="flex items-center gap-2 text-[#C27803]">
                <Award className="w-5 h-5" />
                <h3 className="font-serif text-base font-bold italic text-[#1A1A1A]">
                  Heuristic Claim Boundary (§02)
                </h3>
              </div>
              <p className="text-xs text-[#66615C] leading-relaxed">
                No exact proof claimed. The result is labelled as a feasible solution or gap to reference. In accordance with the claim discipline contract, the word "optimal" is never applied.
              </p>
            </div>
          )}

          {/* Node Inspector Card */}
          {selectedTreeNode && (
            <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-4 shadow-[3px_3px_0px_0px_#1A1A1A] space-y-3">
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#1A1A1A] flex items-center gap-1.5">
                <Binary className="w-4 h-4 text-[#1A1A1A]" />
                <span>Search Node #{selectedTreeNode.id} Inspector</span>
              </h3>

              <div className="space-y-2 font-mono text-xs text-[#1A1A1A]">
                <div className="flex justify-between bg-[#EBE7E4] p-2 border border-[#1A1A1A]/30">
                  <span className="text-[#66615C]">Depth Level:</span>
                  <span className="text-[#1A1A1A] font-bold">{selectedTreeNode.depth}</span>
                </div>
                <div className="flex justify-between bg-[#EBE7E4] p-2 border border-[#1A1A1A]/30">
                  <span className="text-[#66615C]">Lower Bound:</span>
                  <span className="text-[#B84A39] font-bold">{selectedTreeNode.lowerBound}m</span>
                </div>
                <div className="flex justify-between bg-[#EBE7E4] p-2 border border-[#1A1A1A]/30">
                  <span className="text-[#66615C]">Prune State:</span>
                  <span className={selectedTreeNode.pruned ? 'text-[#B84A39] font-bold' : 'text-[#234E3E] font-bold'}>
                    {selectedTreeNode.pruned ? 'PRUNED (LB ≥ Incumbent)' : 'ACTIVE FRONTIER'}
                  </span>
                </div>
                <div className="bg-[#EBE7E4] p-2 border border-[#1A1A1A]/30">
                  <span className="text-[#66615C] block mb-1">Partial Subtour:</span>
                  <span className="text-[#1A1A1A] text-[11px] font-bold">
                    0 → {selectedTreeNode.partialTour.slice(1).join(' → ')}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
