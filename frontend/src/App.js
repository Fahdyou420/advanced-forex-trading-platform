import React from 'react';

function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <h1 className="text-4xl font-bold text-blue-400">Forex Trading Platform</h1>
      <p className="text-gray-400 mt-2">Frontend is working!</p>
      
      <div className="mt-8 bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4 text-blue-400">System Status</h2>
        <p className="text-green-400">✅ Frontend deployed successfully</p>
        <p className="text-yellow-400">⏳ Backend connection pending</p>
      </div>
    </div>
  );
}

export default App;
