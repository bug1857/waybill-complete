import React from 'react';
import {
  Truck,
  ShieldCheck,
  Cpu,
  BarChart3,
  Binary,
  BookOpen,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Upload,
} from 'lucide-react';
import { Instance, SolveReport, SolveStatus } from '../types';

interface HeaderProps {
  activeTab: 'dispatch' | 'sandbox' | 'evidence' | 'asymmetry' | 'invariants' | 'report';
  setActiveTab: (tab: 'dispatch' | 'sandbox' | 'evidence' | 'asymmetry' | 'invariants' | 'report') => void;
  activeInstance: Instance;
  latestReport?: SolveReport;
  onOpenImportModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  activeInstance,
  latestReport,
  onOpenImportModal,
}) => {
  const getStatusBadge = (status?: SolveStatus) => {
    if (!status) return null;

    if (status === SolveStatus.PROVEN_OPTIMAL_TSP) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider bg-[#234E3E]/10 text-[#234E3E] border border-[#234E3E]">
          <CheckCircle2 className="w-3 h-3" /> PROVEN OPTIMAL
        </span>
      );
    }
    if (status === SolveStatus.HEURISTIC_FEASIBLE_CVRPTW) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider bg-[#1A3A5B]/10 text-[#1A3A5B] border border-[#1A3A5B]">
          <ShieldCheck className="w-3 h-3" /> FEASIBLE CVRPTW
        </span>
      );
    }
    if (status === SolveStatus.REFERENCE_GAP_ONLY) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider bg-[#C27803]/10 text-[#C27803] border border-[#C27803]">
          <BarChart3 className="w-3 h-3" /> GAP TO REF
        </span>
      );
    }
    if (status === SolveStatus.EXACT_TIMEOUT_WITH_INCUMBENT) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider bg-[#5A2A42]/10 text-[#5A2A42] border border-[#5A2A42]">
          <Cpu className="w-3 h-3" /> BUDGET TIMEOUT
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider bg-[#B84A39]/10 text-[#B84A39] border border-[#B84A39]">
        <AlertTriangle className="w-3 h-3" /> INFEASIBLE
      </span>
    );
  };

  return (
    <header className="border-b-2 border-[#1A1A1A] bg-[#F7F3F0] sticky top-0 z-40">
      {/* Top Editorial publication banner */}
      <div className="border-b border-[#1A1A1A]/15 bg-[#EBE7E4] px-4 py-1 text-[10px] font-mono uppercase tracking-[0.2em] text-[#66615C]">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <span>Design &amp; Analysis of Algorithms · Research Monograph No. 042</span>
          <span className="hidden sm:inline">Rigorous Proof &amp; Asymmetric Courier Dispatch</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-18">
          {/* Logo & Title */}
          <div className="flex items-center gap-3.5">
            <div className="h-10 w-10 border border-[#1A1A1A] bg-[#1A1A1A] text-[#F7F3F0] flex items-center justify-center shadow-[2px_2px_0px_0px_rgba(26,26,26,0.3)]">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-baseline gap-2.5">
                <span className="font-serif text-2xl tracking-tight text-[#1A1A1A] font-semibold italic">Waybill</span>
                <span className="text-[10px] font-mono uppercase tracking-widest text-[#1A1A1A] border border-[#1A1A1A] px-1.5 py-0.2 bg-[#FAF7F5]">
                  DAA Rev. 2
                </span>
              </div>
              <p className="text-[11px] text-[#66615C] font-mono tracking-tight hidden sm:block">
                Combinatorial Dispatch Engine &amp; Exact Proof Audit System
              </p>
            </div>
          </div>

          {/* Matrix & Integrity Metadata Bar */}
          <div className="hidden xl:flex items-center gap-3 text-xs font-mono text-[#66615C] bg-[#FAF7F5] px-3.5 py-1.5 border border-[#1A1A1A]/30">
            <div>
              <span className="text-[#1A1A1A] font-semibold">Matrix Hash:</span>{' '}
              <span className="text-[#1A1A1A]">{activeInstance.distanceMatrix.hash}</span>
            </div>
            <span className="text-[#1A1A1A]/20">|</span>
            <div>
              <span className="text-[#1A1A1A] font-semibold">Symmetry:</span>{' '}
              {activeInstance.distanceMatrix.isSymmetric ? (
                <span className="text-[#234E3E] font-bold">d(A,B) = d(B,A)</span>
              ) : (
                <span className="text-[#B84A39] font-bold">d(A,B) ≠ d(B,A) (Asymmetric)</span>
              )}
            </div>
            {latestReport && (
              <>
                <span className="text-[#1A1A1A]/20">|</span>
                <div>{getStatusBadge(latestReport.status)}</div>
              </>
            )}
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1.5">
            <button
              id="nav-dispatch"
              onClick={() => setActiveTab('dispatch')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs uppercase tracking-wider font-semibold transition-all border ${
                activeTab === 'dispatch'
                  ? 'bg-[#1A1A1A] text-[#F7F3F0] border-[#1A1A1A] shadow-[2px_2px_0px_0px_rgba(26,26,26,0.3)]'
                  : 'bg-transparent text-[#1A1A1A] border-transparent hover:border-[#1A1A1A]/30 hover:bg-[#EBE7E4]'
              }`}
            >
              <Truck className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Fleet Dispatch</span>
            </button>

            <button
              id="nav-sandbox"
              onClick={() => setActiveTab('sandbox')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs uppercase tracking-wider font-semibold transition-all border ${
                activeTab === 'sandbox'
                  ? 'bg-[#1A1A1A] text-[#F7F3F0] border-[#1A1A1A] shadow-[2px_2px_0px_0px_rgba(26,26,26,0.3)]'
                  : 'bg-transparent text-[#1A1A1A] border-transparent hover:border-[#1A1A1A]/30 hover:bg-[#EBE7E4]'
              }`}
            >
              <Binary className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Solver Prover</span>
            </button>

            <button
              id="nav-asymmetry"
              onClick={() => setActiveTab('asymmetry')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs uppercase tracking-wider font-semibold transition-all border ${
                activeTab === 'asymmetry'
                  ? 'bg-[#1A1A1A] text-[#F7F3F0] border-[#1A1A1A] shadow-[2px_2px_0px_0px_rgba(26,26,26,0.3)]'
                  : 'bg-transparent text-[#1A1A1A] border-transparent hover:border-[#1A1A1A]/30 hover:bg-[#EBE7E4]'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Asymmetry Trap</span>
            </button>

            <button
              id="nav-evidence"
              onClick={() => setActiveTab('evidence')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs uppercase tracking-wider font-semibold transition-all border ${
                activeTab === 'evidence'
                  ? 'bg-[#1A1A1A] text-[#F7F3F0] border-[#1A1A1A] shadow-[2px_2px_0px_0px_rgba(26,26,26,0.3)]'
                  : 'bg-transparent text-[#1A1A1A] border-transparent hover:border-[#1A1A1A]/30 hover:bg-[#EBE7E4]'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Evidence Lab</span>
            </button>

            <button
              id="nav-invariants"
              onClick={() => setActiveTab('invariants')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs uppercase tracking-wider font-semibold transition-all border ${
                activeTab === 'invariants'
                  ? 'bg-[#1A1A1A] text-[#F7F3F0] border-[#1A1A1A] shadow-[2px_2px_0px_0px_rgba(26,26,26,0.3)]'
                  : 'bg-transparent text-[#1A1A1A] border-transparent hover:border-[#1A1A1A]/30 hover:bg-[#EBE7E4]'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Invariant Chain</span>
            </button>

            <button
              id="nav-report"
              onClick={() => setActiveTab('report')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs uppercase tracking-wider font-semibold transition-all border ${
                activeTab === 'report'
                  ? 'bg-[#1A1A1A] text-[#F7F3F0] border-[#1A1A1A] shadow-[2px_2px_0px_0px_rgba(26,26,26,0.3)]'
                  : 'bg-transparent text-[#1A1A1A] border-transparent hover:border-[#1A1A1A]/30 hover:bg-[#EBE7E4]'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Core Thesis</span>
            </button>

            <span className="text-[#1A1A1A]/20 mx-0.5">|</span>

            {/* Dedicated Real Data Importer Trigger */}
            <button
              id="btn-open-import-modal"
              onClick={onOpenImportModal}
              className="flex items-center gap-1.5 px-3 py-2 text-xs uppercase tracking-wider font-bold bg-[#EBE7E4] hover:bg-[#1A1A1A] text-[#1A1A1A] hover:text-[#F7F3F0] border-2 border-[#1A1A1A] shadow-[2px_2px_0px_0px_#1A1A1A] transition-all cursor-pointer"
              title="Upload CSV or JSON Deliveries & Road Matrix"
            >
              <Upload className="w-3.5 h-3.5" />
              <span className="font-mono">Import Data</span>
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
};

