import React, { useState } from 'react';
import axios from 'axios';
import { CloudArrowUpIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';

const DEFAULT_SETTINGS = {
    restock_columns: {
        'upc': ['Upc'], 'pcs': ['PCS'], 'asin': ['ASIN'], 'pk': ['PK'], 'price': ['Price'], 'suplier': ['suplier']
    },
    order_columns: {
        'upc': ['UPC'], 'pcs': ['PCS'], 'asin': ['ASIN 1', 'ASIN 2'], 'sku': ['ASIN1_SKU', 'ASIN2_SKU'], 'pk': ['PK'], 'price': ['price'], 'suplier': ['suplier']
    },
    invoice_columns: {
        'shipquantity': ['ShipQuantity'], 'upc': ['Upc'], 'price': ['NetEach2'], 'packsize': ['PackSize'], 'brand': ['Brand'], 'description': ['Description']
    }
};

export default function ShipmentPage() {
    const [invoiceFile, setInvoiceFile] = useState(null);
    const [restockFiles, setRestockFiles] = useState(null);
    const [orderFiles, setOrderFiles] = useState(null);
    const [dcCode, setDcCode] = useState("");
    const [settings, setSettings] = useState(DEFAULT_SETTINGS);
    const [showSettings, setShowSettings] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async () => {
        if (!invoiceFile || !restockFiles || !orderFiles || !dcCode) {
            alert("Please fill all fields and upload files.");
            return;
        }

        setLoading(true);
        const formData = new FormData();
        formData.append("invoice_file", invoiceFile[0]);
        for (let i = 0; i < restockFiles.length; i++) formData.append("restock_files", restockFiles[i]);
        for (let i = 0; i < orderFiles.length; i++) formData.append("order_files", orderFiles[i]);
        formData.append("dc_code", dcCode);
        formData.append("settings_str", JSON.stringify(settings));

        try {
            const response = await axios.post('http://localhost:8000/api/shipment', formData, { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'Shipment_Result.xlsx');
            document.body.appendChild(link);
            link.click();
        } catch (error) {
            console.error(error);
            alert("Process failed. Check console.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-8 bg-gray-900 min-h-screen text-white">
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-bold">Shipment Creator</h1>
                <button onClick={() => setShowSettings(!showSettings)} className="flex items-center gap-2 text-gray-400 hover:text-white">
                    <Cog6ToothIcon className="h-6 w-6" /> Settings
                </button>
            </div>

            {/* DC CODE INPUT */}
            <div className="mb-8">
                <label className="block text-sm font-medium text-gray-400 mb-2">DC Code</label>
                <input 
                    type="text" 
                    value={dcCode}
                    onChange={(e) => setDcCode(e.target.value)}
                    placeholder="e.g., EU, US"
                    className="w-full md:w-1/3 bg-gray-800 border border-gray-700 rounded p-3 text-white focus:border-blue-500 outline-none"
                />
            </div>

            {/* UPLOAD SECTION */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <UploadCard title="Invoice File (Master)" multiple={false} setFile={setInvoiceFile} files={invoiceFile} />
                <UploadCard title="Order Files" multiple={true} setFile={setOrderFiles} files={orderFiles} />
                <UploadCard title="Restock Files" multiple={true} setFile={setRestockFiles} files={restockFiles} />
            </div>

            <button onClick={handleSubmit} disabled={loading} className={`w-full py-4 rounded-lg font-bold text-lg ${loading ? 'bg-gray-700' : 'bg-green-600 hover:bg-green-500'}`}>
                {loading ? "Processing..." : "Generate Shipment Manifest"}
            </button>
        </div>
    );
}

function UploadCard({ title, multiple, setFile, files }) {
    return (
        <div className="bg-gray-800 p-6 rounded-xl border-2 border-dashed border-gray-700 flex flex-col items-center justify-center h-48">
            <CloudArrowUpIcon className="h-10 w-10 text-gray-500 mb-3" />
            <h3 className="text-lg font-medium text-gray-300 mb-1">{title}</h3>
            <input type="file" multiple={multiple} className="text-sm text-gray-400" onChange={(e) => setFile(e.target.files)} />
            {files && <p className="mt-2 text-green-400 text-sm">{files.length} file(s)</p>}
        </div>
    );
}