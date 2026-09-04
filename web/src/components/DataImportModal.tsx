import React, { useState, useRef } from 'react';
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertTriangle,
  X,
  Download,
  Database,
  Sparkles,
  Truck,
  Layers,
  MapPin,
  Clock,
  Code2,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import { Instance } from '../types';
import {
  FleetOptions,
  parseCsvData,
  parseJsonData,
  ParseResult,
  SAMPLE_CSV_CONTENT,
  SAMPLE_JSON_CONTENT,
} from '../core/import/parser';

interface DataImportModalProps {
  onClose: () => void;
  onImportSuccess: (instance: Instance) => void;
}

export const DataImportModal: React.FC<DataImportModalProps> = ({
  onClose,
  onImportSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<'upload' | 'paste' | 'samples'>('upload');
  const [fileContent, setFileContent] = useState<string>('');
  const [fileName, setFileName] = useState<string>('');
  const [fileType, setFileType] = useState<'csv' | 'json'>('csv');
  const [instanceName, setInstanceName] = useState<string>('Custom Enterprise Dispatch');
  const [isDragging, setIsDragging] = useState(false);

  // Fleet Configuration Options
  const [fleetOptions, setFleetOptions] = useState<FleetOptions>({
    vehicleCount: 3,
    vehicleCapacity: 30,
    maxShiftHours: 8,
    matrixMode: 'ASYMMETRIC_ROAD',
  });

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Parse on the fly to provide live validation feedback
  const parseResult: ParseResult | null = React.useMemo(() => {
    if (!fileContent.trim()) return null;
    if (fileType === 'csv') {
      return parseCsvData(fileContent, fleetOptions, instanceName);
    } else {
      return parseJsonData(fileContent, fleetOptions, instanceName);
    }
  }, [fileContent, fileType, fleetOptions, instanceName]);

  // Handle File Read
  const handleFile = (file: File) => {
    const isJson = file.name.endsWith('.json') || file.type === 'application/json';
    const isCsv = file.name.endsWith('.csv') || file.type === 'text/csv' || file.type === 'text/plain';

    if (!isJson && !isCsv) {
      alert('Please upload a valid .csv or .json file.');
      return;
    }

    const detectedType = isJson ? 'json' : 'csv';
    setFileType(detectedType);
    setFileName(file.name);
    setInstanceName(file.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' '));

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setFileContent(content);
    };
    reader.readAsText(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  // Download Sample Files
  const downloadSample = (type: 'csv' | 'json') => {
    const text = type === 'csv' ? SAMPLE_CSV_CONTENT : SAMPLE_JSON_CONTENT;
    const name = type === 'csv' ? 'sample_deliveries_template.csv' : 'sample_instance_template.json';
    const mime = type === 'csv' ? 'text/csv' : 'application/json';

    const blob = new Blob([text], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Load Preset Sample
  const loadPresetSample = (preset: 'london' | 'tokyo' | 'chicago') => {
    if (preset === 'london') {
      setFileType('csv');
      setFileName('london_west_end_deliveries.csv');
      setInstanceName('London West End Courier Dispatch');
      setFileContent(SAMPLE_CSV_CONTENT);
      setFleetOptions({
        vehicleCount: 2,
        vehicleCapacity: 15,
        maxShiftHours: 8,
        matrixMode: 'ASYMMETRIC_ROAD',
      });
    } else if (preset === 'tokyo') {
      setFileType('json');
      setFileName('tokyo_express_hub.json');
      setInstanceName('Tokyo Express Courier Hub');
      setFileContent(SAMPLE_JSON_CONTENT);
      setFleetOptions({
        vehicleCount: 2,
        vehicleCapacity: 15,
        maxShiftHours: 8,
        matrixMode: 'ASYMMETRIC_ROAD',
      });
    } else {
      // Chicago Grid
      const chicagoCsv = `name,lat,lng,demand,window_start,window_end,service_time_sec,is_depot
Depot (Loop Distribution Hub),41.8781,-87.6298,0,08:00,18:00,0,true
Willis Tower Deliveries,41.8789,-87.6359,4,08:30,10:30,300,false
West Loop Culinary Warehouse,41.8845,-87.6492,5,09:00,11:30,360,false
Fulton Market Tech Office,41.8867,-87.6521,3,09:30,12:00,240,false
River North Luxury Retail,41.8925,-87.6341,2,10:00,12:30,300,false
Magnificent Mile Store,41.8988,-87.6241,4,10:30,13:00,360,false
Streeterville Hospital Supply,41.8942,-87.6189,3,13:00,15:00,300,false
Gold Coast Residences,41.9058,-87.6288,2,13:30,15:30,240,false
Lincoln Park Cafe Goods,41.9214,-87.6425,4,14:00,16:30,360,false
Wicker Park Boutique Hub,41.9088,-87.6775,3,14:30,17:00,300,false
Pilsen Art Studio,41.8562,-87.6612,2,15:00,17:30,240,false
South Loop Commerce Annex,41.8601,-87.6255,4,15:30,17:30,300,false`;

      setFileType('csv');
      setFileName('chicago_metro_logistics.csv');
      setInstanceName('Chicago Metro Asymmetric Logistics');
      setFileContent(chicagoCsv);
      setFleetOptions({
        vehicleCount: 3,
        vehicleCapacity: 20,
        maxShiftHours: 9,
        matrixMode: 'ASYMMETRIC_ROAD',
      });
    }
  };

  const handleFinalImport = () => {
    if (!parseResult || !parseResult.success || !parseResult.instance) return;
    onImportSuccess(parseResult.instance);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1A1A1A]/70 backdrop-blur-xs">
      <div className="bg-[#FAF7F5] border-2 border-[#1A1A1A] w-full max-w-5xl max-h-[92vh] flex flex-col shadow-[6px_6px_0px_0px_#1A1A1A] overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b-2 border-[#1A1A1A] bg-[#EBE7E4]">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 bg-[#1A1A1A] text-[#F7F3F0] flex items-center justify-center font-bold">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-serif text-lg sm:text-xl font-bold italic text-[#1A1A1A]">
                  Import Real Enterprise Delivery Data
                </h2>
                <span className="text-[10px] font-mono uppercase tracking-widest bg-[#1A1A1A] text-[#F7F3F0] px-2 py-0.5 font-bold">
                  CSV · JSON
                </span>
              </div>
              <p className="text-xs text-[#66615C] font-mono">
                Load custom coordinates, delivery time windows, parcel demands, and fleet constraints
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-[#66615C] hover:text-[#1A1A1A] border border-transparent hover:border-[#1A1A1A] hover:bg-[#EBE7E4] transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Top Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-[#1A1A1A]/20 pb-3">
            <div className="flex items-center gap-2 font-mono text-xs">
              <button
                id="btn-tab-upload-file"
                onClick={() => setActiveTab('upload')}
                className={`flex items-center gap-1.5 px-4 py-2 border border-[#1A1A1A] font-bold uppercase tracking-wider transition ${
                  activeTab === 'upload'
                    ? 'bg-[#1A1A1A] text-[#F7F3F0] shadow-[2px_2px_0px_0px_#1A1A1A]'
                    : 'bg-[#FAF7F5] text-[#66615C] hover:text-[#1A1A1A] hover:bg-[#EBE7E4]'
                }`}
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Upload File</span>
              </button>

              <button
                id="btn-tab-paste-raw"
                onClick={() => setActiveTab('paste')}
                className={`flex items-center gap-1.5 px-4 py-2 border border-[#1A1A1A] font-bold uppercase tracking-wider transition ${
                  activeTab === 'paste'
                    ? 'bg-[#1A1A1A] text-[#F7F3F0] shadow-[2px_2px_0px_0px_#1A1A1A]'
                    : 'bg-[#FAF7F5] text-[#66615C] hover:text-[#1A1A1A] hover:bg-[#EBE7E4]'
                }`}
              >
                <Code2 className="w-3.5 h-3.5" />
                <span>Paste CSV / JSON</span>
              </button>

              <button
                id="btn-tab-sample-datasets"
                onClick={() => setActiveTab('samples')}
                className={`flex items-center gap-1.5 px-4 py-2 border border-[#1A1A1A] font-bold uppercase tracking-wider transition ${
                  activeTab === 'samples'
                    ? 'bg-[#1A1A1A] text-[#F7F3F0] shadow-[2px_2px_0px_0px_#1A1A1A]'
                    : 'bg-[#FAF7F5] text-[#66615C] hover:text-[#1A1A1A] hover:bg-[#EBE7E4]'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Quick-Load Samples</span>
              </button>
            </div>

            {/* Template Download Actions */}
            <div className="flex items-center gap-2 font-mono text-xs">
              <button
                onClick={() => downloadSample('csv')}
                className="flex items-center gap-1 bg-[#EBE7E4] hover:bg-[#D1CCC7] text-[#1A1A1A] px-2.5 py-1.5 border border-[#1A1A1A] transition text-[11px] font-bold"
              >
                <Download className="w-3 h-3" />
                <span>Download .CSV Template</span>
              </button>
              <button
                onClick={() => downloadSample('json')}
                className="flex items-center gap-1 bg-[#EBE7E4] hover:bg-[#D1CCC7] text-[#1A1A1A] px-2.5 py-1.5 border border-[#1A1A1A] transition text-[11px] font-bold"
              >
                <Download className="w-3 h-3" />
                <span>Download .JSON Template</span>
              </button>
            </div>
          </div>

          {/* TAB 1: FILE DRAG & DROP UPLOAD */}
          {activeTab === 'upload' && (
            <div className="space-y-4">
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed p-8 text-center cursor-pointer transition-all ${
                  isDragging
                    ? 'border-[#1A1A1A] bg-[#EBE7E4] scale-[1.01]'
                    : 'border-[#1A1A1A]/40 bg-[#FAF7F5] hover:border-[#1A1A1A] hover:bg-[#EBE7E4]/50'
                }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={(e) => e.target.files && handleFile(e.target.files[0])}
                  accept=".csv,.json,text/csv,application/json"
                  className="hidden"
                />
                <Upload className="w-10 h-10 text-[#1A1A1A] mx-auto mb-3" />
                <div className="font-serif text-lg font-semibold italic text-[#1A1A1A]">
                  {fileName ? `Selected File: ${fileName}` : 'Drop your CSV or JSON file here, or click to browse'}
                </div>
                <p className="text-xs font-mono text-[#66615C] mt-1 max-w-md mx-auto">
                  Supports comma-separated spreadsheets with headers (name, lat, lng, demand, window_start, window_end) or standard VRP JSON structures.
                </p>
              </div>
            </div>
          )}

          {/* TAB 2: PASTE RAW TEXT */}
          {activeTab === 'paste' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between font-mono text-xs text-[#66615C]">
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-1.5 cursor-pointer font-bold text-[#1A1A1A]">
                    <input
                      type="radio"
                      name="format"
                      checked={fileType === 'csv'}
                      onChange={() => setFileType('csv')}
                      className="accent-[#1A1A1A]"
                    />
                    <span>CSV Format</span>
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer font-bold text-[#1A1A1A]">
                    <input
                      type="radio"
                      name="format"
                      checked={fileType === 'json'}
                      onChange={() => setFileType('json')}
                      className="accent-[#1A1A1A]"
                    />
                    <span>JSON Format</span>
                  </label>
                </div>
                <span>Paste raw spreadsheet rows or JSON payload below</span>
              </div>

              <textarea
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                placeholder={
                  fileType === 'csv'
                    ? 'name,lat,lng,demand,window_start,window_end\nDepot Central,37.785,-122.405,0,08:00,18:00\nCustomer Stop 1,37.790,-122.401,2,09:00,11:30\nCustomer Stop 2,37.778,-122.412,3,13:00,15:30'
                    : '{\n  "name": "Custom Courier Instance",\n  "stops": [\n    { "name": "Depot", "lat": 37.785, "lng": -122.405, "demand": 0, "isDepot": true },\n    { "name": "Stop 1", "lat": 37.790, "lng": -122.401, "demand": 2 }\n  ]\n}'
                }
                rows={9}
                className="w-full p-4 bg-[#EBE7E4] border-2 border-[#1A1A1A] font-mono text-xs text-[#1A1A1A] focus:outline-none focus:ring-1 focus:ring-[#1A1A1A] leading-relaxed shadow-[2px_2px_0px_0px_#1A1A1A]"
              />
            </div>
          )}

          {/* TAB 3: QUICK LOAD PRESET REAL SAMPLES */}
          {activeTab === 'samples' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div
                onClick={() => loadPresetSample('london')}
                className="p-5 border-2 border-[#1A1A1A] bg-[#FAF7F5] hover:bg-[#EBE7E4] cursor-pointer transition shadow-[2px_2px_0px_0px_#1A1A1A] space-y-2.5 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold bg-[#1A1A1A] text-white px-2 py-0.5">CSV</span>
                    <span className="text-xs font-mono text-[#66615C]">10 Stops · 2 Vans</span>
                  </div>
                  <h3 className="font-serif text-base font-bold italic text-[#1A1A1A] mt-2">
                    London West End Couriers
                  </h3>
                  <p className="text-xs font-sans text-[#66615C] leading-relaxed">
                    Dense retail delivery stops through Covent Garden, Soho, Mayfair, and Bloomsbury with tight delivery windows.
                  </p>
                </div>
                <button className="w-full py-1.5 border border-[#1A1A1A] text-xs font-mono font-bold uppercase bg-[#EBE7E4] hover:bg-[#1A1A1A] hover:text-white transition">
                  Load London Dataset
                </button>
              </div>

              <div
                onClick={() => loadPresetSample('tokyo')}
                className="p-5 border-2 border-[#1A1A1A] bg-[#FAF7F5] hover:bg-[#EBE7E4] cursor-pointer transition shadow-[2px_2px_0px_0px_#1A1A1A] space-y-2.5 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold bg-[#1A1A1A] text-white px-2 py-0.5">JSON</span>
                    <span className="text-xs font-mono text-[#66615C]">8 Stops · 2 Vans</span>
                  </div>
                  <h3 className="font-serif text-base font-bold italic text-[#1A1A1A] mt-2">
                    Tokyo Express Courier Hub
                  </h3>
                  <p className="text-xs font-sans text-[#66615C] leading-relaxed">
                    Commercial parcels covering Shibuya, Omotesando, Roppongi Hills, Ginza, and Akihabara tech towers.
                  </p>
                </div>
                <button className="w-full py-1.5 border border-[#1A1A1A] text-xs font-mono font-bold uppercase bg-[#EBE7E4] hover:bg-[#1A1A1A] hover:text-white transition">
                  Load Tokyo Dataset
                </button>
              </div>

              <div
                onClick={() => loadPresetSample('chicago')}
                className="p-5 border-2 border-[#1A1A1A] bg-[#FAF7F5] hover:bg-[#EBE7E4] cursor-pointer transition shadow-[2px_2px_0px_0px_#1A1A1A] space-y-2.5 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold bg-[#1A1A1A] text-white px-2 py-0.5">CSV</span>
                    <span className="text-xs font-mono text-[#66615C]">12 Stops · 3 Vans</span>
                  </div>
                  <h3 className="font-serif text-base font-bold italic text-[#1A1A1A] mt-2">
                    Chicago Metro Logistics
                  </h3>
                  <p className="text-xs font-sans text-[#66615C] leading-relaxed">
                    Loop, River North, Fulton Market, and Magnificent Mile courier run with high directional street asymmetry.
                  </p>
                </div>
                <button className="w-full py-1.5 border border-[#1A1A1A] text-xs font-mono font-bold uppercase bg-[#EBE7E4] hover:bg-[#1A1A1A] hover:text-white transition">
                  Load Chicago Dataset
                </button>
              </div>
            </div>
          )}

          {/* Dataset Name & Fleet Configuration Parameters */}
          <div className="bg-[#EBE7E4] border-2 border-[#1A1A1A] p-5 shadow-[2px_2px_0px_0px_#1A1A1A] space-y-4">
            <div className="flex items-center justify-between border-b border-[#1A1A1A]/20 pb-2.5">
              <h3 className="font-serif text-sm font-bold italic text-[#1A1A1A] flex items-center gap-2">
                <Truck className="w-4 h-4 text-[#1A1A1A]" />
                <span>Fleet &amp; Distance Model Configuration</span>
              </h3>
              <span className="text-[11px] font-mono text-[#66615C]">
                Applied automatically to the imported instance
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
              <div>
                <label className="text-[#66615C] block mb-1 font-semibold uppercase text-[10px]">
                  Instance Title:
                </label>
                <input
                  type="text"
                  value={instanceName}
                  onChange={(e) => setInstanceName(e.target.value)}
                  className="w-full bg-[#FAF7F5] border border-[#1A1A1A] px-3 py-1.5 text-xs text-[#1A1A1A] focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[#66615C] block mb-1 font-semibold uppercase text-[10px]">
                  Active Fleet Size (Vans):
                </label>
                <select
                  value={fleetOptions.vehicleCount}
                  onChange={(e) =>
                    setFleetOptions({ ...fleetOptions, vehicleCount: Number(e.target.value) })
                  }
                  className="w-full bg-[#FAF7F5] border border-[#1A1A1A] px-3 py-1.5 text-xs text-[#1A1A1A] focus:outline-none cursor-pointer"
                >
                  <option value="1">1 Van (TSP / Single Courier)</option>
                  <option value="2">2 Vans</option>
                  <option value="3">3 Vans</option>
                  <option value="4">4 Vans</option>
                  <option value="6">6 Vans</option>
                  <option value="8">8 Vans</option>
                </select>
              </div>

              <div>
                <label className="text-[#66615C] block mb-1 font-semibold uppercase text-[10px]">
                  Capacity per Van (Parcels):
                </label>
                <input
                  type="number"
                  min="5"
                  max="500"
                  value={fleetOptions.vehicleCapacity}
                  onChange={(e) =>
                    setFleetOptions({
                      ...fleetOptions,
                      vehicleCapacity: Math.max(1, Number(e.target.value)),
                    })
                  }
                  className="w-full bg-[#FAF7F5] border border-[#1A1A1A] px-3 py-1.5 text-xs text-[#1A1A1A] focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[#66615C] block mb-1 font-semibold uppercase text-[10px]">
                  Distance &amp; Matrix Engine:
                </label>
                <select
                  value={fleetOptions.matrixMode}
                  onChange={(e) =>
                    setFleetOptions({
                      ...fleetOptions,
                      matrixMode: e.target.value as any,
                    })
                  }
                  className="w-full bg-[#FAF7F5] border border-[#1A1A1A] px-3 py-1.5 text-xs text-[#1A1A1A] focus:outline-none cursor-pointer"
                >
                  <option value="ASYMMETRIC_ROAD">Asymmetric Street Grid (Real-Road)</option>
                  <option value="HAVERSINE">Haversine GPS WGS84</option>
                  <option value="EUCLIDEAN">Euclidean Planar (EUC_2D)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Validation & Schema Feedback */}
          {parseResult && (
            <div className="space-y-3 font-mono text-xs">
              <div
                className={`p-4 border-2 shadow-[2px_2px_0px_0px_#1A1A1A] flex items-start justify-between gap-4 ${
                  parseResult.success
                    ? 'bg-[#FAF7F5] border-[#234E3E]'
                    : 'bg-[#FAF7F5] border-[#B84A39]'
                }`}
              >
                <div className="flex items-start gap-3">
                  {parseResult.success ? (
                    <CheckCircle2 className="w-5 h-5 text-[#234E3E] shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-[#B84A39] shrink-0 mt-0.5" />
                  )}
                  <div>
                    <h4 className="font-bold text-sm text-[#1A1A1A]">
                      {parseResult.success
                        ? `Valid Instance Ready: ${parseResult.stats?.stopCount} Stops Detected`
                        : 'Dataset Parsing Error'}
                    </h4>
                    {parseResult.success && parseResult.stats && (
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5 text-[#66615C] text-[11px]">
                        <span>
                          Total Load: <strong>{parseResult.stats.totalDemand}</strong> /{' '}
                          {parseResult.stats.totalCapacity} capacity
                        </span>
                        <span>
                          Time Windows:{' '}
                          <strong className={parseResult.stats.hasTimeWindows ? 'text-[#234E3E]' : 'text-[#66615C]'}>
                            {parseResult.stats.hasTimeWindows ? 'Detected (CVRPTW)' : 'None (CVRP)'}
                          </strong>
                        </span>
                        <span>
                          GPS WGS84:{' '}
                          <strong>{parseResult.stats.hasGpsCoords ? 'Yes' : 'Planar'}</strong>
                        </span>
                        <span>
                          Matrix:{' '}
                          <strong>
                            {parseResult.stats.isAsymmetric ? 'Asymmetric d(A,B)≠d(B,A)' : 'Symmetric'}
                          </strong>
                        </span>
                      </div>
                    )}

                    {/* Errors */}
                    {parseResult.errors.length > 0 && (
                      <ul className="mt-2 space-y-1 text-[#B84A39] text-xs">
                        {parseResult.errors.map((err, idx) => (
                          <li key={`err-${idx}`}>• {err}</li>
                        ))}
                      </ul>
                    )}

                    {/* Warnings */}
                    {parseResult.warnings.length > 0 && (
                      <ul className="mt-2 space-y-1 text-[#C27803] text-xs">
                        {parseResult.warnings.map((warn, idx) => (
                          <li key={`warn-${idx}`}>⚠ {warn}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </div>

              {/* Stops Table Preview */}
              {parseResult.instance && (
                <div className="border border-[#1A1A1A] bg-[#FAF7F5] max-h-48 overflow-y-auto">
                  <table className="w-full text-left text-[11px]">
                    <thead className="bg-[#EBE7E4] border-b border-[#1A1A1A] text-[#1A1A1A] sticky top-0">
                      <tr>
                        <th className="py-1.5 px-3 font-bold">#</th>
                        <th className="py-1.5 px-3 font-bold">Location Name</th>
                        <th className="py-1.5 px-3 font-bold">Type</th>
                        <th className="py-1.5 px-3 font-bold">Coords (Lat, Lng / X, Y)</th>
                        <th className="py-1.5 px-3 font-bold">Demand</th>
                        <th className="py-1.5 px-3 font-bold">Time Window</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1A1A1A]/15 text-[#1A1A1A]">
                      {parseResult.instance.stops.slice(0, 15).map((stop) => (
                        <tr key={`preview-stop-${stop.id}`} className="hover:bg-[#EBE7E4]/50">
                          <td className="py-1 px-3 font-mono">{stop.id}</td>
                          <td className="py-1 px-3 font-bold">{stop.name}</td>
                          <td className="py-1 px-3">
                            {stop.isDepot ? (
                              <span className="bg-[#1A1A1A] text-white px-1.5 py-0.5 text-[9px] font-bold uppercase">
                                Depot
                              </span>
                            ) : (
                              <span className="text-[#66615C]">Delivery</span>
                            )}
                          </td>
                          <td className="py-1 px-3 font-mono text-[#66615C]">
                            {stop.lat !== undefined && stop.lng !== undefined
                              ? `${stop.lat.toFixed(4)}, ${stop.lng.toFixed(4)}`
                              : `${stop.x}, ${stop.y}`}
                          </td>
                          <td className="py-1 px-3 font-mono">{stop.demand} pkgs</td>
                          <td className="py-1 px-3 font-mono text-[#66615C]">
                            {stop.window
                              ? `${Math.floor(stop.window.startSec / 3600)}:00 - ${Math.floor(
                                  stop.window.endSec / 3600
                                )}:00`
                              : 'Flexible'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {parseResult.instance.stops.length > 15 && (
                    <div className="text-center py-1.5 text-[10px] text-[#66615C] bg-[#EBE7E4] font-mono">
                      + {parseResult.instance.stops.length - 15} additional stops parsed...
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t-2 border-[#1A1A1A] bg-[#EBE7E4] font-mono text-xs">
          <div className="text-[#66615C] text-xs">
            {parseResult?.success
              ? '✓ Dataset verified against Waybill constraints'
              : 'Select or paste a dataset to begin solving'}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-[#1A1A1A] text-[#1A1A1A] hover:bg-[#FAF7F5] font-bold uppercase tracking-wider transition"
            >
              Cancel
            </button>

            <button
              id="btn-confirm-import-data"
              onClick={handleFinalImport}
              disabled={!parseResult || !parseResult.success}
              className="flex items-center gap-2 bg-[#1A1A1A] hover:bg-[#333333] active:bg-[#000000] text-[#F7F3F0] font-bold uppercase tracking-wider px-5 py-2 border border-[#1A1A1A] shadow-[2px_2px_0px_0px_#1A1A1A] transition disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <span>Import &amp; Solve Instance</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
