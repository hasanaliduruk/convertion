import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import RestockPage from './components/RestockPage';
import ShipmentPage from './components/ShipmentPage';

// 1. The Dashboard (Menu) Component
function Dashboard() {
  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-10">
      <h1 className="text-4xl font-bold mb-12">Inventory Management System</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl w-full">
        {/* Button for Restock App */}
        <Link to="/restock" className="group">
            <div className="bg-gray-800 border-2 border-blue-600 hover:bg-blue-600 transition-all p-8 rounded-xl text-center cursor-pointer shadow-lg hover:shadow-blue-500/50">
                <h2 className="text-2xl font-bold mb-2">Restock Calculator</h2>
                <p className="text-gray-400 group-hover:text-white">Process Ham & Export files</p>
            </div>
        </Link>
        <Link to="/shipment" className="group">
            <div className="bg-gray-800 border-2 border-green-600 hover:bg-green-600 transition-all p-8 rounded-xl text-center shadow-lg">
                <h2 className="text-2xl font-bold mb-2">Shipment Creator</h2>
                <p className="text-gray-400 group-hover:text-white">Generate Manifests</p>
            </div>
        </Link>

        {/* Placeholder for future apps */}
        <div className="bg-gray-800 border-2 border-gray-700 p-8 rounded-xl text-center opacity-50 cursor-not-allowed">
          <h2 className="text-2xl font-bold mb-2">Shipment Creator</h2>
          <p className="text-gray-500">Coming Soon</p>
        </div>
      </div>
    </div>
  );
}

// 2. The Main App Router
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/restock" element={<RestockPage />} />
        <Route path="/shipment" element={<ShipmentPage />} />
      </Routes>
    </Router>
  );
}

export default App;