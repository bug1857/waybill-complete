/**
 * Waybill — Main Application Entry Point
 * Complete DAA Research Platform & Courier Routing Engine
 */

import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { DispatchStudio } from './components/DispatchStudio';
import { SolverSandbox } from './components/SolverSandbox';
import { AsymmetryTrapLab } from './components/AsymmetryTrapLab';
import { EvidenceLab } from './components/EvidenceLab';
import { InvariantRunner } from './components/InvariantRunner';
import { ReportSummary } from './components/ReportSummary';
import { SolveReportModal } from './components/SolveReportModal';
import { DataImportModal } from './components/DataImportModal';
import { Instance, SolveReport } from './types';
import {
  createManhattan150CourierInstance,
  createSanFranciscoCourierInstance,
  createTsplibInstance,
  generateRandomInstance,
} from './core/bench/datasets';
import { solveClarkeWrightSavings } from './core/construct/clarkeWright';
import { Building2, Upload, Sparkles } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<
    'dispatch' | 'sandbox' | 'evidence' | 'asymmetry' | 'invariants' | 'report'
  >('dispatch');

  // Active instance selection
  const [instanceKey, setInstanceKey] = useState<
    'SF_30' | 'MANHATTAN_150' | 'BERLIN_52' | 'EIL_51' | 'BAYG_29' | 'RANDOM_12' | 'CUSTOM'
  >('SF_30');

  const [activeInstance, setActiveInstance] = useState<Instance>(() =>
    createSanFranciscoCourierInstance()
  );

  const [report, setReport] = useState<SolveReport | null>(null);
  const [showReportModal, setShowReportModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  // Re-load instance when dropdown changes
  const handleInstanceChange = (key: typeof instanceKey | 'OPEN_IMPORT') => {
    if (key === 'OPEN_IMPORT') {
      setShowImportModal(true);
      return;
    }

    setInstanceKey(key);
    let newInst: Instance;
    if (key === 'SF_30') {
      newInst = createSanFranciscoCourierInstance();
    } else if (key === 'MANHATTAN_150') {
      newInst = createManhattan150CourierInstance();
    } else if (key === 'BERLIN_52') {
      newInst = createTsplibInstance('berlin52');
    } else if (key === 'EIL_51') {
      newInst = createTsplibInstance('eil51');
    } else if (key === 'ST_70') {
      newInst = createTsplibInstance('st70');
    } else if (key === 'RANDOM_12') {
      newInst = generateRandomInstance(12, 'TSP', true, 12345);
    } else {
      return; // Keep existing custom instance
    }
    setActiveInstance(newInst);

    // Auto-solve with Clarke-Wright for initial view
    const initialSolve = solveClarkeWrightSavings(newInst);
    setReport(initialSolve);
  };

  // Handle custom imported instance
  const handleImportSuccess = (importedInstance: Instance) => {
    setActiveInstance(importedInstance);
    setInstanceKey('CUSTOM');
    const initialSolve = solveClarkeWrightSavings(importedInstance);
    setReport(initialSolve);
    setActiveTab('dispatch');
  };

  // Initial solve on mount
  useEffect(() => {
    const initialSolve = solveClarkeWrightSavings(activeInstance);
    setReport(initialSolve);
  }, []);

  return (
    <div className="min-h-screen bg-[#F7F3F0] text-[#1A1A1A] flex flex-col font-sans">
      {/* Top Header Navigation */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeInstance={activeInstance}
        latestReport={report || undefined}
        onOpenImportModal={() => setShowImportModal(true)}
      />

      {/* Dataset & Quick Instance Selector Sub-bar */}
      <div className="bg-[#EBE7E4] border-b border-[#1A1A1A]/30 px-4 py-2.5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-[#1A1A1A] font-semibold flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
                <Building2 className="w-3.5 h-3.5 text-[#1A1A1A]" />
                <span>Active Problem Instance:</span>
              </span>
              <select
                id="instance-selector"
                value={instanceKey}
                onChange={(e) => handleInstanceChange(e.target.value as any)}
                className="bg-[#FAF7F5] text-[#1A1A1A] border border-[#1A1A1A] py-1 px-3 focus:outline-none focus:ring-1 focus:ring-[#1A1A1A] cursor-pointer font-mono text-xs shadow-[1px_1px_0px_0px_rgba(26,26,26,0.3)]"
              >
                {instanceKey === 'CUSTOM' && (
                  <optgroup label="User Uploaded Data">
                    <option value="CUSTOM">Custom Data: {activeInstance.name}</option>
                  </optgroup>
                )}
                <optgroup label="Real-Road Courier Instances (CVRPTW)">
                  <option value="SF_30">San Francisco Metro (30 Stops · 4 Vans · Asymmetric)</option>
                  <option value="MANHATTAN_150">Manhattan High-Density (150 Stops · 6 Vans · Asymmetric)</option>
                </optgroup>
                <optgroup label="TSPLIB Published Ground Truth (EUC_2D)">
                  <option value="BERLIN_52">TSPLIB: Berlin52 (Published Opt: 7,542m)</option>
                  <option value="EIL_51">TSPLIB: Eil51 (Published Opt: 426m)</option>
                  <option value="ST_70">TSPLIB: st70 (Published Opt: 675)</option>
                </optgroup>
                <optgroup label="Exact Validation Corpus">
                  <option value="RANDOM_12">Small Exact Instance (12 Stops · TSP)</option>
                </optgroup>
                <optgroup label="Import Actions">
                  <option value="OPEN_IMPORT">➕ Upload Custom CSV / JSON...</option>
                </optgroup>
              </select>
            </div>

            <button
              onClick={() => setShowImportModal(true)}
              className="hidden sm:flex items-center gap-1 bg-[#FAF7F5] hover:bg-[#FAF7F5]/80 text-[#1A1A1A] px-2.5 py-1 border border-[#1A1A1A] font-bold text-[11px] uppercase tracking-wider transition shadow-[1px_1px_0px_0px_#1A1A1A]"
            >
              <Upload className="w-3 h-3 text-[#1A1A1A]" />
              <span>Import New File</span>
            </button>
          </div>

          <div className="flex items-center gap-4 text-[#66615C] text-xs">
            <span>
              Type: <strong className="text-[#1A1A1A]">{activeInstance.type}</strong>
            </span>
            <span>
              Stops: <strong className="text-[#1A1A1A]">{activeInstance.stops.length}</strong>
            </span>
            <span>
              Vehicles: <strong className="text-[#1A1A1A]">{activeInstance.vehicles.length}</strong>
            </span>
            <span>
              Matrix:{' '}
              <strong className={activeInstance.distanceMatrix.isSymmetric ? 'text-[#234E3E]' : 'text-[#B84A39]'}>
                {activeInstance.distanceMatrix.isSymmetric ? 'Symmetric' : 'Asymmetric Road'}
              </strong>
            </span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dispatch' && (
          <DispatchStudio
            instance={activeInstance}
            setInstance={setActiveInstance}
            report={report}
            setReport={setReport}
            onOpenReportModal={() => setShowReportModal(true)}
          />
        )}

        {activeTab === 'sandbox' && (
          <SolverSandbox
            instance={activeInstance}
            report={report}
            setReport={setReport}
            onOpenReportModal={() => setShowReportModal(true)}
          />
        )}

        {activeTab === 'asymmetry' && <AsymmetryTrapLab />}

        {activeTab === 'evidence' && <EvidenceLab />}

        {activeTab === 'invariants' && <InvariantRunner />}

        {activeTab === 'report' && <ReportSummary />}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#1A1A1A]/30 bg-[#EBE7E4] py-4 text-center text-xs font-mono text-[#66615C]">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>Waybill · Design &amp; Analysis of Algorithms Project 4 (Revision 2 Architecture)</div>
          <div className="text-[#1A1A1A] font-semibold">
            Strict Claim Discipline: "Proven Best" vs "Best Found" are Never Conflated.
          </div>
        </div>
      </footer>

      {/* Full SolveReport JSON Modal */}
      {showReportModal && report && (
        <SolveReportModal report={report} onClose={() => setShowReportModal(false)} />
      )}

      {/* Real Data CSV / JSON Import Modal */}
      {showImportModal && (
        <DataImportModal
          onClose={() => setShowImportModal(false)}
          onImportSuccess={handleImportSuccess}
        />
      )}
    </div>
  );
}
