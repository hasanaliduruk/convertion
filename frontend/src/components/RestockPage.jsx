import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
    CloudArrowUpIcon, 
    Cog6ToothIcon, 
    ArrowUpIcon, 
    ArrowDownIcon, 
    TrashIcon, 
    DocumentIcon 
} from '@heroicons/react/24/outline';
import { useDropzone } from 'react-dropzone'; // Direct import for the list wrapper
import DragDropZone from './DragDropZone';    // Our new component for the single file

// Default Configuration
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

const generateClientId = () => Math.random().toString(36).substring(7);

export default function RestockPage() {
  // --- STATE ---
  // Changed: files are now arrays, initialized as empty arrays []
  const [hamFiles, setHamFiles] = useState([]);
  const [exportFiles, setExportFiles] = useState([]);
  const [restockFile, setRestockFile] = useState(null);
  
  const [loading, setLoading] = useState(false);
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [showSettings, setShowSettings] = useState(false);

  const [clientId] = useState(generateClientId());
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState(0);
  const logsEndRef = useRef(null);

  // --- WEBSOCKET CONNECTION ---
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}`);
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setLogs(prev => [...prev, `> ${data.message}`]);
        setProgress(data.percent);
    };

    return () => ws.close();
  }, [clientId]);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // --- HANDLERS ---
  const handleSettingsChange = (category, key, value) => {
    setSettings(prev => ({
      ...prev,
      [category]: { ...prev[category], [key]: value }
    }));
  };

  const handleColumnChange = (key, valueString) => {
    const array = valueString.split(',').map(s => s.trim());
    handleSettingsChange('column_mappings', key, array);
  };

  const handleSubmit = async () => {
    if (hamFiles.length === 0 || exportFiles.length === 0 || !restockFile) {
      alert("Please upload all required files.");
      return;
    }

    setLoading(true);
    setLogs(["> Starting upload..."]); // Reset logs
    setProgress(0);
    setLoading(true);
    const formData = new FormData();

    formData.append("client_id", clientId);

    // Append Files (In the explicit order of the array)
    hamFiles.forEach(file => formData.append("ham_files", file));
    exportFiles.forEach(file => formData.append("export_files", file));
    formData.append("restock_file", restockFile[0]);

    // Append Settings
    formData.append("settings_str", JSON.stringify(settings));

    try {
      const response = await axios.post('http://localhost:8000/api/restock', formData, {
        responseType: 'blob', 
      });

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
        <button 
            onClick={() => setShowSettings(!showSettings)}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
            <Cog6ToothIcon className="h-6 w-6" />
            {showSettings ? "Hide Settings" : "Settings"}
        </button>
      </div>

      {/* --- SETTINGS PANEL --- */}
      {showSettings && (
        <div className="bg-gray-800 p-6 rounded-lg mb-8 border border-gray-700 animate-in fade-in slide-in-from-top-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                    <h3 className="text-blue-400 font-bold mb-4 uppercase text-sm tracking-wider">Column Names</h3>
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
                <div>
                    <h3 className="text-green-400 font-bold mb-4 uppercase text-sm tracking-wider">Supplier Costs</h3>
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
        <FileReorderList 
            title="Ham Files" 
            files={hamFiles} 
            setFiles={setHamFiles} 
            color="blue" 
            description="..." 
        />
        
        <FileReorderList 
            title="Export Files" 
            files={exportFiles} 
            setFiles={setExportFiles} 
            color="purple" 
            description="..." 
        />
        
        {/* Single File Drop Zone */}
        <DragDropZone 
            title="Restock Excel (Master)" 
            multiple={false} 
            onFilesAdded={(files) => setRestockFile(files)} 
            currentFiles={restockFile} 
        />
      </div>

      <button
        onClick={handleSubmit}
        disabled={loading}
        className={`w-full py-4 rounded-lg font-bold text-lg shadow-lg transition-all ${
          loading 
            ? 'bg-gray-700 cursor-wait text-gray-400' 
            : 'bg-blue-600 hover:bg-blue-500 text-white hover:shadow-blue-500/25'
        }`}
      >
        {loading ? "Processing..." : "Run Restock Process"}
      </button>
      {/* --- LOGGING TERMINAL (NEW) --- */}
      <div className="mb-8 bg-black rounded-lg border border-gray-700 p-4 font-mono text-xs md:text-sm shadow-2xl">
        <div className="flex justify-between items-center mb-2 border-b border-gray-800 pb-2">
            <span className="text-gray-400">Process Terminal</span>
            <span className="text-blue-500">{progress}%</span>
        </div>
        
        {/* Progress Bar */}
        <div className="w-full bg-gray-800 rounded-full h-2.5 mb-4">
            <div 
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-out" 
                style={{ width: `${progress}%` }}
            ></div>
        </div>

        {/* Log Output */}
        <div className="h-40 overflow-y-auto space-y-1 text-green-400">
            {logs.length === 0 && <span className="text-gray-600 opacity-50">Waiting for jobs...</span>}
            {logs.map((log, i) => (
                <div key={i} className="break-words">{log}</div>
            ))}
            <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}

// --- NEW COMPONENT: Reorderable File List ---
function FileReorderList({ title, files, setFiles, color, description }) {
    const handleUpload = (e) => {
        const newFiles = Array.from(e.target.files);
        // Append new files to the list
        setFiles(prev => [...prev, ...newFiles]);
        // Reset input value to allow re-uploading same file if needed
        e.target.value = null; 
    };

    const moveFile = (index, direction) => {
        const newFiles = [...files];
        if (direction === 'up' && index > 0) {
            [newFiles[index - 1], newFiles[index]] = [newFiles[index], newFiles[index - 1]];
        } else if (direction === 'down' && index < newFiles.length - 1) {
            [newFiles[index + 1], newFiles[index]] = [newFiles[index], newFiles[index + 1]];
        }
        setFiles(newFiles);
    };

    const removeFile = (index) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const onDrop = (acceptedFiles) => {
        setFiles(prev => [...prev, ...acceptedFiles]);
    };

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']}
    });

    return (
        <div {...getRootProps()} className={`bg-gray-800 p-6 rounded-xl border border-gray-700 flex flex-col h-[500px]`}>
            <input {...getInputProps()} /> {/* Hidden Input */}
            <div className="flex justify-between items-start mb-4">
                <div>
                    <h3 className={`text-lg font-bold text-${color}-400`}>{title}</h3>
                    <p className="text-xs text-gray-500 mt-1">{description}</p>
                </div>
                <label className="cursor-pointer">
                    <span className={`bg-${color}-600 hover:bg-${color}-500 text-white text-xs px-3 py-1 rounded transition-colors flex items-center gap-1`}>
                        <CloudArrowUpIcon className="h-4 w-4" /> Add
                    </span>
                    <input type="file" multiple className="hidden" onChange={handleUpload} accept=".xlsx,.xls" />
                </label>
            </div>

            {/* List Container */}
            <div className="flex-1 overflow-y-auto bg-gray-900 rounded-lg p-2 space-y-2 border border-gray-700">
                {/* Drag Overlay Message */}
                {isDragActive && (
                    <div className="absolute inset-0 bg-black/80 flex items-center justify-center z-10 rounded-lg">
                        <p className={`text-${color}-400 font-bold`}>Drop files to add!</p>
                    </div>
                )}
                {files.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-gray-600 text-sm italic">
                        Drag & Drop files here
                    </div>
                ) : (
                    files.map((file, index) => (
                        <div key={index} className="flex items-center justify-between bg-gray-800 p-2 rounded border border-gray-700 group hover:border-gray-500 transition-colors" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center gap-2 overflow-hidden">
                                <span className="text-gray-500 text-xs font-mono">#{index + 1}</span>
                                <DocumentIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
                                <span className="text-sm text-gray-200 truncate" title={file.name}>{file.name}</span>
                            </div>
                            
                            <div className="flex items-center gap-1 opacity-100 md:opacity-0 group-hover:opacity-100 transition-opacity">
                                <button 
                                    onClick={() => moveFile(index, 'up')}
                                    disabled={index === 0}
                                    className="p-1 hover:bg-gray-700 rounded disabled:opacity-30 text-gray-400 hover:text-white"
                                >
                                    <ArrowUpIcon className="h-4 w-4" />
                                </button>
                                <button 
                                    onClick={() => moveFile(index, 'down')}
                                    disabled={index === files.length - 1}
                                    className="p-1 hover:bg-gray-700 rounded disabled:opacity-30 text-gray-400 hover:text-white"
                                >
                                    <ArrowDownIcon className="h-4 w-4" />
                                </button>
                                <button 
                                    onClick={() => removeFile(index)}
                                    className="p-1 hover:bg-red-900/50 rounded text-gray-500 hover:text-red-400 ml-2"
                                >
                                    <TrashIcon className="h-4 w-4" />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>
            <div className="mt-2 text-right text-xs text-gray-500">
                Total: {files.length}
            </div>
        </div>
    );
}

// Simple Upload Card (For single files)
function UploadCard({ title, multiple, setFile, files }) {
  return (
    <div className="bg-gray-800 p-6 rounded-xl border-2 border-dashed border-gray-700 hover:border-gray-500 transition-colors flex flex-col items-center justify-center h-[500px] group">
      <CloudArrowUpIcon className="h-12 w-12 text-gray-500 group-hover:text-blue-400 mb-3 transition-colors" />
      <h3 className="text-lg font-medium text-gray-300 mb-1">{title}</h3>
      <label className="cursor-pointer">
        <span className="bg-gray-700 hover:bg-gray-600 text-white text-xs px-3 py-1 rounded transition-colors">
            Choose File
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
          <div className="mt-4 bg-green-900/30 text-green-400 text-sm px-3 py-2 rounded border border-green-900/50 flex items-center gap-2">
              <DocumentIcon className="h-5 w-5" />
              {files[0].name}
          </div>
      )}
    </div>
  );
}