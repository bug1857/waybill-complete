import React, { useState } from 'react';
import {
  Layers,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  Zap,
  Info,
  ShieldCheck,
  SplitSquareVertical,
} from 'lucide-react';
import { Stop } from '../types';
import {
  createAsymmetricRoadMatrix,
  createHaversineMatrix,
} from '../core/distance/matrix';
import { improveOrOpt } from '../core/local/orOpt';
import { demonstrateAsymmetryTrap, improveTwoOpt } from '../core/local/twoOpt';
import { solveNearestNeighbour } from '../core/construct/nearestNeighbour';
import { calculateTourCost } from '../core/eval/feasibility';

export const AsymmetryTrapLab: React.FC = () => {
  const [stopCount, setStopCount] = useState<number>(10);
  const [seed, setSeed] = useState<number>(42);
  const [activeStep, setActiveStep] = useState<number>(1);

  // Generate synthetic stops
  const stops: Stop[] = Array.from({ length: stopCount }, (_, i) => ({
    id: i,
    name: i === 0 ? 'Depot Hub' : `Stop #${i}`,
    x: 100 + ((i * 137) % 500),
    y: 80 + ((i * 211) % 350),
    lat: 37.77 + ((i * 137) % 500) * 0.0002,
    lng: -122.42 + ((i * 211) % 350) * 0.0002,
    demand: 1,
    serviceTimeSec: 180,
    isDepot: i === 0,
  }));

  const symMatrix = createHaversineMatrix(stops);
  const asymMatrix = createAsymmetricRoadMatrix(stops, 0.4); // 40% asymmetry

  // Initial tour
  const sampleTour = [0];
  for (let i = 1; i < stopCount; i++) sampleTour.push(i);
  sampleTour.push(0);

  // Diagnostic trap demo
  const trapDemo = demonstrateAsymmetryTrap(sampleTour, asymMatrix.matrix);

  // Solve on symmetric matrix
  const symTourCost = calculateTourCost(sampleTour, symMatrix.matrix);
  const symTwoOpt = improveTwoOpt(sampleTour, symMatrix.matrix, true);

  // Solve on asymmetric matrix with naive O(1) vs honest O(k)
  const asymTourCost = calculateTourCost(sampleTour, asymMatrix.matrix);
  const asymHonestTwoOpt = improveTwoOpt(sampleTour, asymMatrix.matrix, false, false);
  const asymNaiveTwoOpt = improveTwoOpt(sampleTour, asymMatrix.matrix, false, true); // forced naive
  const asymOrOpt = improveOrOpt(sampleTour, asymMatrix.matrix);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-6 shadow-[3px_3px_0px_0px_#1A1A1A]">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold uppercase tracking-widest px-2.5 py-0.5 bg-[#B84A39] text-white">
                DAA Revision 2 · Section §07
              </span>
              <span className="text-xs text-[#66615C] font-mono">
                Theorem: d(A,B) ≠ d(B,A) Invalidates Textbook 2-Opt
              </span>
            </div>
            <h1 className="font-serif text-2xl sm:text-3xl font-semibold italic text-[#1A1A1A] mt-2">
              The Asymmetry Trap &amp; Local Search Correctness
            </h1>
            <p className="text-xs text-[#66615C] font-sans mt-1 max-w-3xl leading-relaxed">
              Why straight-line distance assumptions break textbook algorithms on real road networks, and why Or-Opt relocation is mandatory.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              id="btn-regen-asym-sample"
              onClick={() => setSeed((s) => s + 1)}
              className="flex items-center gap-1.5 bg-[#1A1A1A] hover:bg-[#333333] text-[#F7F3F0] text-xs font-mono font-bold uppercase tracking-wider px-4 py-2 border border-[#1A1A1A] transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Regenerate Instance</span>
            </button>
          </div>
        </div>
      </div>

      {/* Visual Explanation Diagram: Before vs After Reversal (§07) */}
      <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-6 shadow-[3px_3px_0px_0px_#1A1A1A] space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-[#1A1A1A]">
          <h2 className="font-serif text-lg font-semibold italic text-[#1A1A1A] flex items-center gap-2">
            <SplitSquareVertical className="w-4 h-4 text-[#1A1A1A]" />
            <span>Mathematical Breakdown: 2-Opt Edge Reversal Mechanics</span>
          </h2>
          <span className="text-xs font-mono text-[#66615C]">
            Proof of O(1) vs O(k) Evaluation Cost
          </span>
        </div>

        {/* The Reversal Diagram */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-mono text-xs">
          {/* Left: Symmetric Case */}
          <div className="bg-[#EBE7E4] p-5 border-2 border-[#234E3E] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[#234E3E] font-bold uppercase">
                1. Symmetric Matrix (d(x,y) = d(y,x))
              </span>
              <span className="text-[10px] bg-[#234E3E] text-white px-2 py-0.5 font-bold">
                O(1) Textbook Valid
              </span>
            </div>

            <div className="p-3 bg-[#FAF7F5] border border-[#1A1A1A]/30 text-[#1A1A1A] space-y-1 text-[11px]">
              <div><strong>Tour Before:</strong> a → b → [m → n] → c → d</div>
              <div><strong>Tour After:</strong> a → c → [n → m] → b → d</div>
              <div className="text-[#66615C] pt-1">
                Segment <span className="text-[#C27803] font-bold">[b .. c]</span> is reversed. Every internal edge <span className="text-[#1A1A1A] font-bold">(x,y)</span> becomes <span className="text-[#1A1A1A] font-bold">(y,x)</span>.
              </div>
            </div>

            <div className="p-3 bg-[#FAF7F5] border border-[#234E3E]/40 text-[#234E3E] space-y-1">
              <div className="font-bold">Delta Formula:</div>
              <div className="text-[12px] font-bold text-[#1A1A1A]">
                Δ = d(a,c) + d(b,d) − d(a,b) − d(c,d)
              </div>
              <p className="text-[11px] text-[#66615C] mt-1 font-sans">
                Because d(m,n) = d(n,m), the internal reversal has <strong>zero net cost change</strong>. The formula evaluates in constant time O(1).
              </p>
            </div>
          </div>

          {/* Right: Asymmetric Case */}
          <div className="bg-[#EBE7E4] p-5 border-2 border-[#B84A39] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[#B84A39] font-bold uppercase">
                2. Real Asymmetric Road Network (d(x,y) ≠ d(y,x))
              </span>
              <span className="text-[10px] bg-[#B84A39] text-white px-2 py-0.5 font-bold">
                O(k) Re-summation Mandatory
              </span>
            </div>

            <div className="p-3 bg-[#FAF7F5] border border-[#1A1A1A]/30 text-[#1A1A1A] space-y-1 text-[11px]">
              <div><strong>Tour Before:</strong> a → b → [m → n] → c → d</div>
              <div><strong>Tour After:</strong> a → c → [n → m] → b → d</div>
              <div className="text-[#66615C] pt-1">
                On one-way streets, driving <span className="text-[#B84A39] font-bold">n → m</span> requires a detour around the bridge compared to <span className="text-[#234E3E] font-bold">m → n</span>.
              </div>
            </div>

            <div className="p-3 bg-[#FAF7F5] border border-[#B84A39]/40 text-[#B84A39] space-y-1">
              <div className="font-bold">Honest Delta Formula:</div>
              <div className="text-[12px] font-bold text-[#1A1A1A]">
                Δ = 4-terms + <span className="text-[#B84A39]">Σ [d(v_next, v_curr) − d(v_curr, v_next)]</span>
              </div>
              <p className="text-[11px] text-[#66615C] mt-1 font-sans">
                Using the 4-term formula silently optimizes the <strong>wrong objective function</strong>, producing broken routes.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Live Discrepancy Audit Inspector on Current Instance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Box 1: Textbook 4-term Naive Predictor */}
        <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-5 shadow-[3px_3px_0px_0px_#1A1A1A] space-y-3 font-mono text-xs">
          <div className="text-[10px] font-bold text-[#66615C] uppercase tracking-wider">
            Textbook Naive 4-Term Move
          </div>
          <div className="p-3 bg-[#EBE7E4] border border-[#1A1A1A]/30">
            <div className="text-[#66615C] text-[11px]">Predicted Delta:</div>
            <div className="text-xl font-bold text-[#C27803] mt-1">
              {trapDemo.naivePredictedDelta} metres
            </div>
          </div>
          <p className="text-[#66615C] text-[11px] leading-relaxed font-sans">
            Computed using textbook Δ = d(a,c)+d(b,d)−d(a,b)−d(c,d), ignoring one-way road reversals.
          </p>
        </div>

        {/* Box 2: Honest Asymmetric Delta */}
        <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-5 shadow-[3px_3px_0px_0px_#1A1A1A] space-y-3 font-mono text-xs">
          <div className="text-[10px] font-bold text-[#66615C] uppercase tracking-wider">
            Real Road Actual Delta
          </div>
          <div className="p-3 bg-[#EBE7E4] border border-[#1A1A1A]/30">
            <div className="text-[#66615C] text-[11px]">True Tour Change:</div>
            <div className="text-xl font-bold text-[#B84A39] mt-1">
              {trapDemo.actualDelta} metres
            </div>
          </div>
          <p className="text-[#66615C] text-[11px] leading-relaxed font-sans">
            Includes all internal edge cost changes along the reversed segment on the road network.
          </p>
        </div>

        {/* Box 3: Silent Discrepancy Error */}
        <div className="bg-[#FAF7F5] border-2 border-[#B84A39] p-5 shadow-[3px_3px_0px_0px_#1A1A1A] space-y-3 font-mono text-xs">
          <div className="text-[10px] font-bold text-[#B84A39] uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Formula Error Gap</span>
          </div>
          <div className="p-3 bg-[#B84A39]/10 border border-[#B84A39]/30">
            <div className="text-[#66615C] text-[11px]">Unaccounted Error:</div>
            <div className="text-xl font-bold text-[#B84A39] mt-1">
              {trapDemo.errorMetres} metres
            </div>
          </div>
          <p className="text-[#1A1A1A] text-[11px] leading-relaxed font-sans">
            {trapDemo.explanation}
          </p>
        </div>
      </div>

      {/* Solver Performance Comparison under Asymmetry */}
      <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-6 shadow-[3px_3px_0px_0px_#1A1A1A] space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#1A1A1A]">
          <h2 className="font-serif text-lg font-semibold italic text-[#1A1A1A]">
            Local Search Comparison on Identical Real-Road Stops
          </h2>
          <span className="text-xs font-mono text-[#234E3E] font-bold">
            Or-Opt Relocation vs Guarded 2-Opt
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-[#1A1A1A] text-[#66615C]">
                <th className="pb-3 font-bold uppercase text-[10px] tracking-wider">Algorithm Operator</th>
                <th className="pb-3 font-bold uppercase text-[10px] tracking-wider">Asymmetry Safe?</th>
                <th className="pb-3 font-bold uppercase text-[10px] tracking-wider">Evaluation Cost</th>
                <th className="pb-3 font-bold uppercase text-[10px] tracking-wider">Resulting Tour Length</th>
                <th className="pb-3 font-bold uppercase text-[10px] tracking-wider">Validity Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1A1A1A]/20 text-[#1A1A1A]">
              <tr>
                <td className="py-3 font-bold">Or-Opt / Relocate (Lengths 1,2,3)</td>
                <td className="py-3">
                  <span className="inline-flex items-center gap-1 text-[#234E3E] font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5" /> 100% Safe (No Reversal)
                  </span>
                </td>
                <td className="py-3 text-[#66615C]">O(1) Constant Time</td>
                <td className="py-3 font-bold text-[#234E3E]">{(asymOrOpt.cost / 1000).toFixed(2)} km</td>
                <td className="py-3 text-[#234E3E] font-bold">Valid &amp; Honest</td>
              </tr>

              <tr>
                <td className="py-3 font-bold">2-Opt with Symmetry Guard (Honest O(k))</td>
                <td className="py-3">
                  <span className="inline-flex items-center gap-1 text-[#1A3A5B] font-bold">
                    <ShieldCheck className="w-3.5 h-3.5" /> Guarded (Re-sums Edges)
                  </span>
                </td>
                <td className="py-3 text-[#66615C]">O(k) Linear Time</td>
                <td className="py-3 font-bold text-[#1A3A5B]">{(asymHonestTwoOpt.cost / 1000).toFixed(2)} km</td>
                <td className="py-3 text-[#1A3A5B] font-bold">Valid (Corrected Delta)</td>
              </tr>

              <tr className="bg-[#B84A39]/10">
                <td className="py-3 font-bold text-[#B84A39]">Textbook 2-Opt (Naive O(1) Formula)</td>
                <td className="py-3">
                  <span className="inline-flex items-center gap-1 text-[#B84A39] font-bold">
                    <AlertTriangle className="w-3.5 h-3.5" /> BROKEN (Silent Error)
                  </span>
                </td>
                <td className="py-3 text-[#66615C]">O(1) (False Assumption)</td>
                <td className="py-3 font-bold text-[#B84A39]">{(asymNaiveTwoOpt.cost / 1000).toFixed(2)} km</td>
                <td className="py-3 text-[#B84A39] font-bold">Confidently Wrong</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
