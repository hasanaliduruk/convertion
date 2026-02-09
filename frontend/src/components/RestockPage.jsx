import React, { useState } from 'react';
import axios from 'axios';
import { CloudArrowUpIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';

// 1. Default Configuration
const DEFAULT_SETTINGS = {
    column_mappings: {
        'upc': ['UPC', 'upc', 'Upc', 'UPC #'],
        'brand': ['BRAND', 'Brand', 'brand'],
        'price': ['NET_AMOUNT', 'Price', 'price'],
        'case': ['CASEPACK', 'Size', 'Case', 'case', 'size'],
        'quantity': ['Qty on Hand', 'Quantity Available', 'Quantity'],
        'pk': ['PK', 'pk', 'PK ']
    },
    supplier_costs: {
        "41 cost": 0.78, "41 standart": 0.78,
        "45 cost": 0.78, "45 standart": 0.78,
        "19 cost": 0.78, "19 standart": 0.78,
        "27 cost": 1.10, "27 standart": 1.10,
        "18 cost": 1.10, "18 standart": 1.10,
        "01 cost": 1.10, "01 standart": 1.10,
        "NF": 0.78
    }
};

export default function RestockPage() {
  // --- STATE ---
  const [hamFiles, setHamFiles] = useState(null);
  const [exportFiles, setExportFiles] = useState(null);
  const [restockFile, setRestockFile] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // New: Settings State
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [showSettings, setShowSettings] = useState(false);

  // --- HANDLERS ---
  const handleSettingsChange = (category, key, value) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }));
  };

  const handleColumnChange = (key, valueString) => {
    // Convert "UPC, upc" string back to array ["UPC", "upc"]
    const array = valueString.split(',').map(s => s.trim());
    handleSettingsChange('column_mappings', key, array);
  };

  const handleSubmit = async () => {
    if (!hamFiles || !exportFiles || !restockFile) {
      alert("Please upload all required files.");
      return;
    }

    setLoading(true);
    const formData = new FormData();

    // 1. Append Files
    for (let i = 0; i < hamFiles.length; i++) formData.append("ham_files", hamFiles[i]);
    for (let i = 0; i < exportFiles.length; i++) formData.append("export_files", exportFiles[i]);
    formData.append("restock_file", restockFile[0]);

    // 2. Append Settings (CRITICAL STEP YOU MISSED)
    formData.append("settings_str", JSON.stringify(settings));

    try {
      const response = await axios.post('http://localhost:8000/api/restock', formData, {
        responseType: 'blob', 
      });

      // Download Logic
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'Restock_Result.xlsx');
      document.body.appendChild(link);
      link.click();
      
    } catch (error) {
      console.error("Processing failed", error);
      alert("Error processing files. Check console.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 bg-gray-900 min-h-screen text-white">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Restock Calculator</h1>
        
        {/* Settings Toggle Button */}
        <button 
            onClick={() => setShowSettings(!showSettings)}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
            <Cog6ToothIcon className="h-6 w-6" />
            {showSettings ? "Hide Settings" : "Settings"}
        </button>
      </div>

      {/* --- SETTINGS PANEL (Hidden by default) --- */}
      {showSettings && (
        <div className="bg-gray-800 p-6 rounded-lg mb-8 border border-gray-700 animate-in fade-in slide-in-from-top-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Column Mappings */}
                <div>
                    <h3 className="text-blue-400 font-bold mb-4 uppercase text-sm tracking-wider">Column Name Definitions</h3>
                    {Object.entries(settings.column_mappings).map(([key, values]) => (
                        <div key={key} className="mb-3">
                            <label className="block text-xs text-gray-500 uppercase mb-1">{key}</label>
                            <input 
                                type="text" 
                                value={values.join(", ")}
                                onChange={(e) => handleColumnChange(key, e.target.value)}
                                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                            />
                        </div>
                    ))}
                </div>

                {/* Supplier Costs */}
                <div>
                    <h3 className="text-green-400 font-bold mb-4 uppercase text-sm tracking-wider">Supplier Added Costs</h3>
                    <div className="grid grid-cols-2 gap-4">
                        {Object.entries(settings.supplier_costs).map(([key, value]) => (
                            <div key={key} className="flex flex-col">
                                <label className="text-xs text-gray-500 mb-1">{key}</label>
                                <input 
                                    type="number" 
                                    step="0.01"
                                    value={value}
                                    onChange={(e) => handleSettingsChange('supplier_costs', key, parseFloat(e.target.value))}
                                    className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm focus:border-green-500 focus:outline-none"
                                />
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
      )}

      {/* --- UPLOAD SECTION --- */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <UploadCard title="Ham Files (Source)" multiple={true} setFile={setHamFiles} files={hamFiles} />
        <UploadCard title="Export Files (Compare)" multiple={true} setFile={setExportFiles} files={exportFiles} />
        <UploadCard title="Restock Excel (Master)" multiple={false} setFile={setRestockFile} files={restockFile} />
      </div>

      {/* --- ACTION BUTTON --- */}
      <button
        onClick={handleSubmit}
        disabled={loading}
        className={`w-full py-4 rounded-lg font-bold text-lg shadow-lg transition-all ${
          loading 
            ? 'bg-gray-700 cursor-wait text-gray-400' 
            : 'bg-blue-600 hover:bg-blue-500 text-white hover:shadow-blue-500/25'
        }`}
      >
        {loading ? (
            <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing Data...
            </span>
        ) : "Run Restock Process"}
      </button>
    </div>
  );
}

// Helper Component
function UploadCard({ title, multiple, setFile, files }) {
  return (
    <div className="bg-gray-800 p-6 rounded-xl border-2 border-dashed border-gray-700 hover:border-gray-500 transition-colors flex flex-col items-center justify-center h-48 group">
      <CloudArrowUpIcon className="h-10 w-10 text-gray-500 group-hover:text-blue-400 mb-3 transition-colors" />
      <h3 className="text-lg font-medium text-gray-300 mb-1">{title}</h3>
      <label className="cursor-pointer">
        <span className="bg-gray-700 hover:bg-gray-600 text-white text-xs px-3 py-1 rounded transition-colors">
            Choose Files
        </span>
        <input
            type="file"
            multiple={multiple}
            className="hidden"
            onChange={(e) => setFile(e.target.files)}
            accept=".xlsx,.xls"
        />
      </label>
      {files && files.length > 0 && (
          <div className="mt-3 bg-green-900/30 text-green-400 text-xs px-2 py-1 rounded border border-green-900/50">
              {files.length} file(s) ready
          </div>
      )}
    </div>
  );
}