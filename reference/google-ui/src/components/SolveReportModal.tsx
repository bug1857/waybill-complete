import React, { useState } from 'react';
import { X, Copy, Check, ShieldCheck, Terminal, Download } from 'lucide-react';
import { SolveReport } from '../types';

interface SolveReportModalProps {
  report: SolveReport;
  onClose: () => void;
}

export const SolveReportModal: React.FC<SolveReportModalProps> = ({ report, onClose }) => {
  const [copied, setCopied] = useState(false);

  const jsonString = JSON.stringify(report, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `solve-report-${report.solver_config_hash}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1A1A1A]/70 backdrop-blur-xs">
      <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] w-full max-w-4xl max-h-[90vh] flex flex-col shadow-[6px_6px_0px_0px_#1A1A1A] overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b-2 border-[#1A1A1A] bg-[#EBE7E4]">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 bg-[#1A1A1A] text-[#F7F3F0] flex items-center justify-center font-bold">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[#1A1A1A] font-mono uppercase tracking-wider">
                SolveReport Contract Inspector (§02, §06)
              </h2>
              <p className="text-xs text-[#66615C] font-mono">
                Typed provenance certificate &amp; independent constraint audit
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 bg-[#FAF7F5] hover:bg-[#EBE7E4] text-[#1A1A1A] text-xs font-mono font-bold uppercase tracking-wider px-3 py-1.5 border border-[#1A1A1A] transition shadow-[1px_1px_0px_0px_#1A1A1A]"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-[#234E3E]" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy JSON'}</span>
            </button>

            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 bg-[#FAF7F5] hover:bg-[#EBE7E4] text-[#1A1A1A] text-xs font-mono font-bold uppercase tracking-wider px-3 py-1.5 border border-[#1A1A1A] transition shadow-[1px_1px_0px_0px_#1A1A1A]"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 text-[#66615C] hover:text-[#1A1A1A] border border-transparent hover:border-[#1A1A1A] hover:bg-[#EBE7E4] transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body: Contract Metadata Grid & Raw JSON */}
        <div className="p-6 overflow-y-auto space-y-5 font-mono text-xs">
          {/* Summary Row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-[#EBE7E4] p-3 border border-[#1A1A1A]/40">
              <span className="text-[#66615C] block text-[10px] uppercase font-bold">STATUS</span>
              <span className="text-[#B84A39] font-bold text-xs mt-1 block truncate">
                {report.status}
              </span>
            </div>

            <div className="bg-[#EBE7E4] p-3 border border-[#1A1A1A]/40">
              <span className="text-[#66615C] block text-[10px] uppercase font-bold">OBJECTIVE VALUE</span>
              <span className="text-[#1A1A1A] font-bold text-xs mt-1 block">
                {report.objective_value} {report.objective_units}
              </span>
            </div>

            <div className="bg-[#EBE7E4] p-3 border border-[#1A1A1A]/40">
              <span className="text-[#66615C] block text-[10px] uppercase font-bold">MATRIX HASH</span>
              <span className="text-[#1A1A1A] font-bold text-xs mt-1 block truncate">
                {report.distance_matrix_hash}
              </span>
            </div>

            <div className="bg-[#EBE7E4] p-3 border border-[#1A1A1A]/40">
              <span className="text-[#66615C] block text-[10px] uppercase font-bold">WALL TIME</span>
              <span className="text-[#1A1A1A] font-bold text-xs mt-1 block">
                {report.wall_time_ms} ms
              </span>
            </div>
          </div>

          {/* Raw JSON Code Block */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[#66615C] text-xs">
              <span className="flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-[#1A1A1A]" />
                <span className="font-bold uppercase tracking-wider text-[11px] text-[#1A1A1A]">Raw SolveReport Schema Output</span>
              </span>
              <span className="text-[11px]">UTF-8 JSON</span>
            </div>

            <pre className="p-4 bg-[#EBE7E4] border-2 border-[#1A1A1A] text-[#1A1A1A] text-xs font-mono overflow-x-auto max-h-[380px] leading-relaxed select-all">
              {jsonString}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
