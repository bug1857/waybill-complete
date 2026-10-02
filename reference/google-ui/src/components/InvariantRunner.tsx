import React, { useState } from 'react';
import {
  ShieldCheck,
  Play,
  CheckCircle2,
  AlertOctagon,
  AlertTriangle,
  RotateCcw,
  Binary,
  Cpu,
  Layers,
} from 'lucide-react';
import {
  InvariantTestResult,
  runInvariantTestSuite,
} from '../core/bench/experiments';

export const InvariantRunner: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [testResults, setTestResults] = useState<InvariantTestResult[] | null>(null);
  const [sampleSize, setSampleSize] = useState<number>(200);

  const handleRun = () => {
    setIsRunning(true);
    setTimeout(() => {
      const results = runInvariantTestSuite(sampleSize);
      setTestResults(results);
      setIsRunning(false);
    }, 40);
  };

  const allPassed = testResults && testResults.every((t) => t.passed);
  const totalTested = testResults
    ? testResults.reduce((acc, t) => acc + t.instancesTested, 0)
    : 0;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-6 shadow-[3px_3px_0px_0px_#1A1A1A]">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold uppercase tracking-widest px-2.5 py-0.5 bg-[#1A1A1A] text-[#F7F3F0]">
                DAA Revision 2 · Section §08 &amp; §09
              </span>
              <span className="text-xs text-[#66615C] font-mono">
                The Unbroken Validation Chain (Zero-Tolerance Invariants)
              </span>
            </div>
            <h1 className="font-serif text-2xl sm:text-3xl font-semibold italic text-[#1A1A1A] mt-2">
              Property-Based Invariant Verification Engine
            </h1>
            <p className="text-xs text-[#66615C] font-sans mt-1 max-w-3xl leading-relaxed">
              Automated fuzz testing across random instances to guarantee no lower bound ever exceeds the true optimum and all solvers mutually agree.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={sampleSize}
              onChange={(e) => setSampleSize(Number(e.target.value))}
              className="bg-[#FAF7F5] text-[#1A1A1A] border border-[#1A1A1A] text-xs font-mono py-2 px-3 focus:outline-none cursor-pointer shadow-[1px_1px_0px_0px_#1A1A1A]"
            >
              <option value="100">Fast Suite (100 Instances)</option>
              <option value="250">Standard Suite (250 Instances)</option>
              <option value="500">Exhaustive Suite (500 Instances)</option>
            </select>

            <button
              id="btn-run-invariants"
              onClick={handleRun}
              disabled={isRunning}
              className="flex items-center gap-1.5 bg-[#1A1A1A] hover:bg-[#333333] active:bg-[#000000] text-[#F7F3F0] text-xs font-mono font-bold uppercase tracking-wider px-5 py-2 border border-[#1A1A1A] transition disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{isRunning ? 'Fuzz Testing...' : 'Execute Invariant Suite'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Validation Chain Overview Diagram (§08) */}
      <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-6 shadow-[3px_3px_0px_0px_#1A1A1A] space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#1A1A1A]">
          <h2 className="font-serif text-lg font-semibold italic text-[#1A1A1A] flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#1A1A1A]" />
            <span>The Unbroken Validation Chain Architecture (§08)</span>
          </h2>
          <span className="text-xs font-mono text-[#66615C]">
            No Problem Size Band is Left Unchecked
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
          {/* Band 1 */}
          <div className="bg-[#EBE7E4] p-4 border border-[#1A1A1A]/40 space-y-2">
            <div className="flex items-center justify-between text-[#66615C]">
              <span className="text-[#B84A39] font-bold">Band 1: n ≤ 12</span>
              <span className="text-[10px] bg-[#1A1A1A] text-white px-1.5 py-0.5 font-bold">Root of Trust</span>
            </div>
            <div className="text-[#1A1A1A] font-bold">Brute Force Ground Truth</div>
            <p className="text-[#66615C] text-[11px] leading-relaxed font-sans">
              Exhaustive enumeration checks every valid permutation, producing the mathematical root of truth.
            </p>
          </div>

          {/* Band 2 */}
          <div className="bg-[#EBE7E4] p-4 border border-[#1A1A1A]/40 space-y-2">
            <div className="flex items-center justify-between text-[#66615C]">
              <span className="text-[#1A3A5B] font-bold">Band 2: 13 ≤ n ≤ 51</span>
              <span className="text-[10px] bg-[#1A1A1A] text-white px-1.5 py-0.5 font-bold">Mutual Agreement</span>
            </div>
            <div className="text-[#1A1A1A] font-bold">HK DP ≡ B&amp;B (All Bounds)</div>
            <p className="text-[#66615C] text-[11px] leading-relaxed font-sans">
              Three independent code paths (subset DP, assignment B&amp;B, 1-tree B&amp;B) agree identically on every instance.
            </p>
          </div>

          {/* Band 3 */}
          <div className="bg-[#EBE7E4] p-4 border border-[#1A1A1A]/40 space-y-2">
            <div className="flex items-center justify-between text-[#66615C]">
              <span className="text-[#234E3E] font-bold">Band 3: n ≥ 52</span>
              <span className="text-[10px] bg-[#1A1A1A] text-white px-1.5 py-0.5 font-bold">External Truth</span>
            </div>
            <div className="text-[#1A1A1A] font-bold">TSPLIB Published Optima</div>
            <p className="text-[#66615C] text-[11px] leading-relaxed font-sans">
              Standard literature benchmarks scored under verified EUC_2D integer rounding conventions.
            </p>
          </div>
        </div>
      </div>

      {/* Test Results Battery */}
      {testResults ? (
        <div className="space-y-4">
          <div
            className={`p-4 border-2 font-mono text-xs flex items-center justify-between shadow-[2px_2px_0px_0px_#1A1A1A] ${
              allPassed
                ? 'bg-[#FAF7F5] border-[#234E3E] text-[#234E3E]'
                : 'bg-[#FAF7F5] border-[#B84A39] text-[#B84A39]'
            }`}
          >
            <div className="flex items-center gap-3">
              {allPassed ? (
                <CheckCircle2 className="w-6 h-6 text-[#234E3E] shrink-0" />
              ) : (
                <AlertOctagon className="w-6 h-6 text-[#B84A39] shrink-0" />
              )}
              <div>
                <div className="text-sm font-bold text-[#1A1A1A]">
                  {allPassed
                    ? `All 5 Invariants 100% Passed (${totalTested} Instances Verified)`
                    : 'Invariant Violations Detected!'}
                </div>
                <div className="text-[#66615C] text-[11px] mt-0.5 font-sans">
                  Zero over-optimistic lower bounds · Zero cross-solver disagreements · Strict asymmetry consistency.
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-3 font-mono text-xs">
            {testResults.map((res, idx) => (
              <div
                key={`inv-${idx}`}
                className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-4 shadow-[2px_2px_0px_0px_#1A1A1A] flex flex-col md:flex-row md:items-center justify-between gap-3"
              >
                <div className="flex items-start gap-3">
                  {res.passed ? (
                    <CheckCircle2 className="w-5 h-5 text-[#234E3E] mt-0.5 shrink-0" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-[#B84A39] mt-0.5 shrink-0" />
                  )}
                  <div>
                    <div className="text-sm font-bold text-[#1A1A1A] flex items-center gap-2">
                      <span>{res.name}</span>
                      <span className="text-[10px] bg-[#EBE7E4] text-[#1A1A1A] border border-[#1A1A1A]/40 px-2 py-0.5 font-bold font-mono">
                        {res.category}
                      </span>
                    </div>
                    <p className="text-[#66615C] text-[11px] mt-1 leading-relaxed font-sans">
                      {res.sampleDetails}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4 shrink-0 text-right md:border-l md:border-[#1A1A1A]/30 md:pl-4">
                  <div>
                    <div className="text-[#66615C] text-[10px] font-bold">TESTS</div>
                    <div className="text-[#1A1A1A] font-bold">{res.instancesTested}</div>
                  </div>
                  <div>
                    <div className="text-[#66615C] text-[10px] font-bold">FAILURES</div>
                    <div className={res.failureCount === 0 ? 'text-[#234E3E] font-bold' : 'text-[#B84A39] font-bold'}>
                      {res.failureCount}
                    </div>
                  </div>
                  <div>
                    <div className="text-[#66615C] text-[10px] font-bold">EXEC TIME</div>
                    <div className="text-[#66615C]">{res.executionTimeMs}ms</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] p-10 text-center space-y-3 shadow-[3px_3px_0px_0px_#1A1A1A]">
          <ShieldCheck className="w-12 h-12 text-[#66615C] mx-auto" />
          <h3 className="text-base font-bold text-[#1A1A1A] font-serif italic">
            Invariant Suite Ready for Execution
          </h3>
          <p className="text-xs text-[#66615C] font-mono max-w-md mx-auto">
            Click <strong>"Execute Invariant Suite"</strong> to run automated property tests across randomized instances.
          </p>
        </div>
      )}
    </div>
  );
};
