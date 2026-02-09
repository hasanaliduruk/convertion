import React, { useState } from 'react';
import axios from 'axios';
import { CloudArrowUpIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';
import DragDropZone from './DragDropZone';

// Default Configuration
const DEFAULT_SETTINGS = {
    restock_columns: {
        'upc': ['Upc'], 'pcs': ['PCS'], 'asin': ['ASIN'], 'pk': ['PK'], 'price': ['Price'], 'suplier': ['suplier']
    },
    order_columns: {
        'upc': ['UPC'], 'pcs': ['PCS'], 'asin': ['ASIN 1', 'ASIN 2', 'ASIN 3'], 'sku': ['ASIN1_SKU', 'ASIN2_SKU'], 'pk': ['PK'], 'price': ['price'], 'suplier': ['suplier']
    },
    invoice_columns: {
        'shipquantity': ['ShipQuantity'], 'upc': ['Upc'], 'price': ['NetEach2'], 'packsize': ['PackSize'], 'brand': ['Brand'], 'description': ['Description']
    }
};

export default function ShipmentPage() {
    // --- STATE ---
    const [invoiceFile, setInvoiceFile] = useState(null);
    const [restockFiles, setRestockFiles] = useState(null);
    const [orderFiles, setOrderFiles] = useState(null);
    const [dcCode, setDcCode] = useState("");
    
    // Settings State
    const [settings, setSettings] = useState(DEFAULT_SETTINGS);
    const [showSettings, setShowSettings] = useState(false);
    
    const [loading, setLoading] = useState(false);

    // --- HANDLERS ---
    const handleColumnChange = (section, key, valueString) => {
        const array = valueString.split(',').map(s => s.trim());
        setSettings(prev => ({
            ...prev,
            [section]: {
                ...prev[section],
                [key]: array
            }
        }));
    };

    const handleSubmit = async () => {
        if (!invoiceFile || !restockFiles || !orderFiles || !dcCode) {
            alert("Please fill all fields (DC Code) and upload all files.");
            return;
        }

        setLoading(true);
        const formData = new FormData();
        
        // Append Files
        formData.append("invoice_file", invoiceFile[0]);
        for (let i = 0; i < restockFiles.length; i++) formData.append("restock_files", restockFiles[i]);
        for (let i = 0; i < orderFiles.length; i++) formData.append("order_files", orderFiles[i]);
        
        // Append Data
        formData.append("dc_code", dcCode);
        formData.append("settings_str", JSON.stringify(settings));

        try {
            const response = await axios.post('http://localhost:8000/api/shipment', formData, { 
                responseType: 'blob' 
            });
            
            // Download
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'Shipment_Result.xlsx');
            document.body.appendChild(link);
            link.click();
        } catch (error) {
            console.error(error);
            alert("Process failed. Check console for details.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-8 bg-gray-900 min-h-screen text-white">
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-bold">Shipment Creator</h1>
                <button 
                    onClick={() => setShowSettings(!showSettings)} 
                    className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
                >
                    <Cog6ToothIcon className="h-6 w-6" /> 
                    {showSettings ? "Hide Settings" : "Settings"}
                </button>
            </div>

            {/* --- SETTINGS PANEL (THIS WAS MISSING BEFORE) --- */}
            {showSettings && (
                <div className="bg-gray-800 p-6 rounded-lg mb-8 border border-gray-700 grid grid-cols-1 md:grid-cols-3 gap-6 animate-in fade-in slide-in-from-top-4">
                    
                    {/* 1. Restock Columns */}
                    <div>
                        <h3 className="text-blue-400 font-bold mb-3 uppercase text-xs tracking-wider">Restock Columns</h3>
                        {Object.entries(settings.restock_columns).map(([key, values]) => (
                            <div key={key} className="mb-2">
                                <label className="block text-xs text-gray-500 uppercase mb-1">{key}</label>
                                <input 
                                    type="text" 
                                    value={values.join(", ")}
                                    onChange={(e) => handleColumnChange('restock_columns', key, e.target.value)}
                                    className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs focus:border-blue-500 focus:outline-none"
                                />
                            </div>
                        ))}
                    </div>

                    {/* 2. Order Columns */}
                    <div>
                        <h3 className="text-green-400 font-bold mb-3 uppercase text-xs tracking-wider">Order Columns</h3>
                        {Object.entries(settings.order_columns).map(([key, values]) => (
                            <div key={key} className="mb-2">
                                <label className="block text-xs text-gray-500 uppercase mb-1">{key}</label>
                                <input 
                                    type="text" 
                                    value={values.join(", ")}
                                    onChange={(e) => handleColumnChange('order_columns', key, e.target.value)}
                                    className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs focus:border-green-500 focus:outline-none"
                                />
                            </div>
                        ))}
                    </div>

                    {/* 3. Invoice Columns */}
                    <div>
                        <h3 className="text-purple-400 font-bold mb-3 uppercase text-xs tracking-wider">Invoice Columns</h3>
                        {Object.entries(settings.invoice_columns).map(([key, values]) => (
                            <div key={key} className="mb-2">
                                <label className="block text-xs text-gray-500 uppercase mb-1">{key}</label>
                                <input 
                                    type="text" 
                                    value={values.join(", ")}
                                    onChange={(e) => handleColumnChange('invoice_columns', key, e.target.value)}
                                    className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs focus:border-purple-500 focus:outline-none"
                                />
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* --- MAIN INPUTS --- */}
            <div className="mb-8">
                <label className="block text-sm font-medium text-gray-400 mb-2">DC Code (Required)</label>
                <input 
                    type="text" 
                    value={dcCode}
                    onChange={(e) => setDcCode(e.target.value)}
                    placeholder="e.g. EU, US (Prefix for SKU)"
                    className="w-full md:w-1/3 bg-gray-800 border border-gray-700 rounded p-3 text-white focus:border-blue-500 outline-none"
                />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <DragDropZone 
                    title="Invoice File (Master)" 
                    multiple={false} 
                    onFilesAdded={(files) => setInvoiceFile(files)} 
                    currentFiles={invoiceFile}
                />
                <DragDropZone 
                    title="Order Files" 
                    multiple={true} 
                    onFilesAdded={(files) => setOrderFiles(files)} 
                    currentFiles={orderFiles}
                />
                <DragDropZone 
                    title="Restock Files" 
                    multiple={true} 
                    onFilesAdded={(files) => setRestockFiles(files)} 
                    currentFiles={restockFiles}
                />
            </div>

            <button 
                onClick={handleSubmit} 
                disabled={loading} 
                className={`w-full py-4 rounded-lg font-bold text-lg transition-all ${
                    loading ? 'bg-gray-700 cursor-wait text-gray-400' : 'bg-green-600 hover:bg-green-500 text-white shadow-lg hover:shadow-green-500/25'
                }`}
            >
                {loading ? "Processing Manifest..." : "Generate Shipment Manifest"}
            </button>
        </div>
    );
}

// Helper Component
function UploadCard({ title, multiple, setFile, files }) {
    return (
        <div className="bg-gray-800 p-6 rounded-xl border-2 border-dashed border-gray-700 hover:border-gray-500 transition-colors flex flex-col items-center justify-center h-48 group">
            <CloudArrowUpIcon className="h-10 w-10 text-gray-500 group-hover:text-green-400 mb-3 transition-colors" />
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