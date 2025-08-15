// Frontend Trading Dashboard - React + Tailwind
// Complete dashboard for the trading platform

import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

// Main Dashboard Component
const TradingDashboard = () => {
  const [prices, setPrices] = useState({});
  const [signals, setSignals] = useState([]);
  const [trades, setTrades] = useState([]);
  const [performance, setPerformance] = useState({ strategies: [], overall: {} });
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [selectedPair, setSelectedPair] = useState('EURUSD');
  const [manualSignal, setManualSignal] = useState({
    strategy_name: 'manual',
    pair: 'EURUSD',
    signal_type: 'BUY',
    entry_price: '',
    stop_loss: '',
    take_profit: '',
    confidence: 0.8
  });
  
  const ws = useRef(null);

  // WebSocket connection
  useEffect(() => {
    connectWebSocket();
    fetchInitialData();
    
    // Cleanup on unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      ws.current = new WebSocket(WS_URL);
      
      ws.current.onopen = () => {
        setConnectionStatus('connected');
        console.log('WebSocket connected');
      };
      
      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'price_update') {
          setPrices(data.data);
        } else if (data.type === 'new_signals') {
          setSignals(prev => [...data.data, ...prev].slice(0, 50));
        }
      };
      
      ws.current.onclose = () => {
        setConnectionStatus('disconnected');
        console.log('WebSocket disconnected');
        
        // Reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
      };
      
      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
      setConnectionStatus('error');
    }
  };

  const fetchInitialData = async () => {
    try {
      // Fetch current prices
      const pricesResponse = await fetch(`${API_BASE_URL}/prices`);
      const pricesData = await pricesResponse.json();
      setPrices(pricesData.prices || {});
      
      // Fetch recent signals
      const signalsResponse = await fetch(`${API_BASE_URL}/signals`);
      const signalsData = await signalsResponse.json();
      setSignals(signalsData.signals || []);
      
      // Fetch trades
      const tradesResponse = await fetch(`${API_BASE_URL}/trades`);
      const tradesData = await tradesResponse.json();
      setTrades(tradesData.trades || []);
      
      // Fetch performance
      const performanceResponse = await fetch(`${API_BASE_URL}/performance`);
      const performanceData = await performanceResponse.json();
      setPerformance(performanceData);
      
    } catch (error) {
      console.error('Error fetching initial data:', error);
    }
  };

  const submitManualSignal = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/signals/manual`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'forex_2025_secure'
        },
        body: JSON.stringify({
          ...manualSignal,
          risk_reward_ratio: Math.abs(manualSignal.take_profit - manualSignal.entry_price) / 
                            Math.abs(manualSignal.stop_loss - manualSignal.entry_price)
        })
      });
      
      if (response.ok) {
        alert('Manual signal created successfully!');
        fetchInitialData(); // Refresh data
        
        // Reset form
        setManualSignal({
          strategy_name: 'manual',
          pair: 'EURUSD',
          signal_type: 'BUY',
          entry_price: '',
          stop_loss: '',
          take_profit: '',
          confidence: 0.8
        });
      } else {
        alert('Error creating signal');
      }
    } catch (error) {
      console.error('Error submitting manual signal:', error);
      alert('Error submitting signal');
    }
  };

  // Format currency pairs for display
  const formatPair = (pair) => {
    return `${pair.slice(0, 3)}/${pair.slice(3, 6)}`;
  };

  // Format price based on pair
  const formatPrice = (price, pair) => {
    if (pair && pair.includes('JPY')) {
      return price.toFixed(3);
    }
    return price.toFixed(5);
  };

  // Calculate price change color
  const getPriceChangeColor = (pair) => {
    const priceData = prices[pair];
    if (!priceData) return 'text-gray-400';
    
    // Simple price change calculation (you might want to store previous prices)
    return 'text-green-400'; // Placeholder
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-blue-400">Forex Trading Platform</h1>
            <p className="text-gray-400 mt-2">Real-time signals • Paper trading • Performance analytics</p>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className={`flex items-center space-x-2 px-4 py-2 rounded-lg ${
              connectionStatus === 'connected' ? 'bg-green-900 text-green-400' :
              connectionStatus === 'disconnected' ? 'bg-red-900 text-red-400' :
              'bg-yellow-900 text-yellow-400'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                connectionStatus === 'connected' ? 'bg-green-400' :
                connectionStatus === 'disconnected' ? 'bg-red-400' :
                'bg-yellow-400'
              }`}></div>
              <span className="text-sm font-medium">{connectionStatus.toUpperCase()}</span>
            </div>
            
            <div className="bg-blue-900 text-blue-400 px-4 py-2 rounded-lg">
              <span className="text-sm font-medium">PAPER MODE</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left Column - Prices & Manual Trading */}
        <div className="space-y-6">
          
          {/* Live Prices */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4 text-blue-400">Live Prices</h2>
            <div className="space-y-3">
              {Object.entries(prices).map(([pair, priceData]) => (
                <div key={pair} 
                     className={`flex justify-between items-center p-3 rounded cursor-pointer transition-colors ${
                       selectedPair === pair ? 'bg-blue-900' : 'bg-gray-700 hover:bg-gray-600'
                     }`}
                     onClick={() => setSelectedPair(pair)}>
                  <div>
                    <div className="font-semibold">{formatPair(pair)}</div>
                    <div className="text-xs text-gray-400">
                      Spread: {(priceData.spread * 10000).toFixed(1)} pips
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`font-mono text-lg ${getPriceChangeColor(pair)}`}>
                      {formatPrice(priceData.price, pair)}
                    </div>
                    <div className="text-xs text-gray-400">
                      {formatPrice(priceData.bid, pair)} / {formatPrice(priceData.ask, pair)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Manual Signal Creation */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4 text-blue-400">Manual Signal</h2>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <select 
                  value={manualSignal.pair}
                  onChange={(e) => setManualSignal(prev => ({ ...prev, pair: e.target.value }))}
                  className="bg-gray-700 border border-gray-600 rounded p-2 text-white">
                  {Object.keys(prices).map(pair => (
                    <option key={pair} value={pair}>{formatPair(pair)}</option>
                  ))}
                </select>
                
                <select 
                  value={manualSignal.signal_type}
                  onChange={(e) => setManualSignal(prev => ({ ...prev, signal_type: e.target.value }))}
                  className="bg-gray-700 border border-gray-600 rounded p-2 text-white">
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                </select>
              </div>
              
              <div className="grid grid-cols-3 gap-4">
                <input
                  type="number"
                  step="0.00001"
                  placeholder="Entry Price"
                  value={manualSignal.entry_price}
                  onChange={(e) => setManualSignal(prev => ({ ...prev, entry_price: e.target.value }))}
                  className="bg-gray-700 border border-gray-600 rounded p-2 text-white placeholder-gray-400"
                />
                
                <input
                  type="number"
                  step="0.00001"
                  placeholder="Stop Loss"
                  value={manualSignal.stop_loss}
                  onChange={(e) => setManualSignal(prev => ({ ...prev, stop_loss: e.target.value }))}
                  className="bg-gray-700 border border-gray-600 rounded p-2 text-white placeholder-gray-400"
                />
                
                <input
                  type="number"
                  step="0.00001"
                  placeholder="Take Profit"
                  value={manualSignal.take_profit}
                  onChange={(e) => setManualSignal(prev => ({ ...prev, take_profit: e.target.value }))}
                  className="bg-gray-700 border border-gray-600 rounded p-2 text-white placeholder-gray-400"
                />
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Confidence: {(manualSignal.confidence * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="1"
                  step="0.05"
                  value={manualSignal.confidence}
                  onChange={(e) => setManualSignal(prev => ({ ...prev, confidence: parseFloat(e.target.value) }))}
                  className="w-full"
                />
              </div>
              
              <button
                onClick={submitManualSignal}
                disabled={!manualSignal.entry_price || !manualSignal.stop_loss || !manualSignal.take_profit}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded transition-colors">
                Create Signal
              </button>
            </div>
          </div>
        </div>

        {/* Middle Column - Signals & Trades */}
        <div className="space-y-6">
          
          {/* Recent Signals */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4 text-blue-400">Recent Signals</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {signals.slice(0, 10).map((signal, index) => (
                <div key={signal.id || index} 
                     className={`p-4 rounded-lg border-l-4 ${
                       signal.signal_type === 'BUY' ? 'border-green-400 bg-green-900/20' : 'border-red-400 bg-red-900/20'
                     }`}>
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <div className="font-semibold text-lg">
                        {formatPair(signal.pair)}
                        <span className={`ml-2 px-2 py-1 text-xs rounded ${
                          signal.signal_type === 'BUY' ? 'bg-green-600' : 'bg-red-600'
                        }`}>
                          {signal.signal_type}
                        </span>
                      </div>
                      <div className="text-sm text-gray-400 capitalize">
                        {signal.strategy_name.replace(/_/g, ' ')}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-mono">
                        {formatPrice(signal.entry_price, signal.pair)}
                      </div>
                      <div className={`text-sm px-2 py-1 rounded ${
                        signal.confidence >= 0.8 ? 'bg-green-600' :
                        signal.confidence >= 0.6 ? 'bg-yellow-600' : 'bg-red-600'
                      }`}>
                        {(signal.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">SL</div>
                      <div className="font-mono">{formatPrice(signal.stop_loss, signal.pair)}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">TP</div>
                      <div className="font-mono">{formatPrice(signal.take_profit, signal.pair)}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">R:R</div>
                      <div className="font-semibold">{signal.risk_reward_ratio?.toFixed(1) || 'N/A'}</div>
                    </div>
                  </div>
                  
                  {signal.created_at && (
                    <div className="text-xs text-gray-500 mt-2">
                      {new Date(signal.created_at).toLocaleString()}
                    </div>
                  )}
                </div>
              ))}
              
              {signals.length === 0 && (
                <div className="text-center text-gray-400 py-8">
                  No signals generated yet
                </div>
              )}
            </div>
          </div>

          {/* Active Trades */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4 text-blue-400">Active Trades</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {trades.filter(trade => trade.status === 'OPEN').slice(0, 10).map((trade, index) => (
                <div key={trade.id || index} className="bg-gray-700 p-4 rounded-lg">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <div className="font-semibold text-lg">
                        {formatPair(trade.pair)}
                        <span className={`ml-2 px-2 py-1 text-xs rounded ${
                          trade.signal_type === 'BUY' ? 'bg-green-600' : 'bg-red-600'
                        }`}>
                          {trade.signal_type || 'UNKNOWN'}
                        </span>
                      </div>
                      <div className="text-sm text-gray-400 capitalize">
                        {trade.strategy_name.replace(/_/g, ' ')}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-mono">
                        {formatPrice(trade.entry_price, trade.pair)}
                      </div>
                      <div className="text-sm text-gray-400">
                        Size: ${trade.position_size?.toFixed(0) || 'N/A'}
                      </div>
                    </div>
                  </div>
                  
                  {trade.pnl !== null && (
                    <div className={`text-sm font-semibold ${
                      trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      P&L: ${trade.pnl.toFixed(2)}
                    </div>
                  )}
                  
                  {trade.created_at && (
                    <div className="text-xs text-gray-500 mt-2">
                      Opened: {new Date(trade.created_at).toLocaleString()}
                    </div>
                  )}
                </div>
              ))}
              
              {trades.filter(trade => trade.status === 'OPEN').length === 0 && (
                <div className="text-center text-gray-400 py-8">
                  No active trades
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column - Performance & Analytics */}
        <div className="space-y-6">
          
          {/* Overall Performance */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4 text-blue-400">Overall Performance</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-700 p-4 rounded-lg text-center">
                <div className="text-2xl font-bold text-green-400">
                  {performance.overall.total_trades || 0}
                </div>
                <div className="text-sm text-gray-400">Total Trades</div>
              </div>
              
              <div className="bg-gray-700 p-4 rounded-lg text-center">
                <div className="text-2xl font-bold text-blue-400">
                  {performance.overall.win_rate?.toFixed(1) || 0}%
                </div>
                <div className="text-sm text-gray-400">Win Rate</div>
              </div>
              
              <div className="bg-gray-700 p-4 rounded-lg text-center">
                <div className={`text-2xl font-bold ${
                  (performance.overall.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  ${performance.overall.total_pnl?.toFixed(2) || '0.00'}
                </div>
                <div className="text-sm text-gray-400">Total P&L</div>
              </div>
              
              <div className="bg-gray-700 p-4 rounded-lg text-center">
                <div className={`text-2xl font-bold ${
                  (performance.overall.avg_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  ${performance.overall.avg_pnl?.toFixed(2) || '0.00'}
                </div>
                <div className="text-sm text-gray-400">Avg P&L</div>
              </div>
            </div>
          </div>

          {/* Strategy Performance */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4 text-blue-400">Strategy Performance</h2>
            <div className="space-y-3">
              {performance.strategies.map((strategy, index) => (
                <div key={strategy.name || index} className="bg-gray-700 p-4 rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <div className="font-semibold capitalize">
                      {strategy.name.replace(/_/g, ' ')}
                    </div>
                    <div className={`px-2 py-1 rounded text-sm ${
                      (strategy.performance_score || 0) >= 0.7 ? 'bg-green-600' :
                      (strategy.performance_score || 0) >= 0.5 ? 'bg-yellow-600' : 'bg-red-600'
                    }`}>
                      {((strategy.performance_score || 0) * 100).toFixed(0)}%
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <div className="text-gray-400">Win Rate</div>
                      <div>{((strategy.win_rate || 0) * 100).toFixed(1)}%</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Avg P&L</div>
                      <div className={`${
                        (strategy.avg_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        ${(strategy.avg_pnl || 0).toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400">Trades</div>
                      <div>{strategy.total_trades || 0}</div>
                    </div>
                  </div>
                </div>
              ))}
              
              {performance.strategies.length === 0 && (
                <div className="text-center text-gray-400 py-8">
                  No strategy data yet
                </div>
              )}
            </div>
          </div>

          {/* Recent Closed Trades */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4 text-blue-400">Recent Closed Trades</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {trades.filter(trade => trade.status === 'CLOSED').slice(0, 5).map((trade, index) => (
                <div key={trade.id || index} className="bg-gray-700 p-3 rounded-lg">
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="font-semibold">{formatPair(trade.pair)}</div>
                      <div className="text-xs text-gray-400 capitalize">
                        {trade.strategy_name.replace(/_/g, ' ')}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`font-bold ${
                        (trade.pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        ${(trade.pnl || 0).toFixed(2)}
                      </div>
                      <div className="text-xs text-gray-400">
                        {trade.closed_at && new Date(trade.closed_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              
              {trades.filter(trade => trade.status === 'CLOSED').length === 0 && (
                <div className="text-center text-gray-400 py-4">
                  No closed trades yet
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Section - Charts */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Price Chart */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4 text-blue-400">
            Price Chart - {formatPair(selectedPair)}
          </h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={[]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="time" stroke="#9CA3AF" />
                <YAxis stroke="#9CA3AF" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }} 
                />
                <Line 
                  type="monotone" 
                  dataKey="price" 
                  stroke="#60A5FA" 
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="text-center text-gray-400 mt-4">
            Price history chart will display here
          </div>
        </div>

        {/* Strategy Performance Chart */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4 text-blue-400">Strategy Comparison</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={performance.strategies}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="name" 
                  stroke="#9CA3AF"
                  tick={{ fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis stroke="#9CA3AF" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                  formatter={(value, name) => [
                    name === 'performance_score' ? `${(value * 100).toFixed(1)}%` : value.toFixed(2),
                    name === 'performance_score' ? 'Performance Score' : 
                    name === 'win_rate' ? 'Win Rate' : 'Avg P&L'
                  ]}
                />
                <Bar dataKey="performance_score" fill="#60A5FA" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 text-center text-gray-500">
        <p>Forex Trading Platform v1.0 • Paper Trading Mode • Real-time data via ExchangeRate API</p>
      </div>
    </div>
  );
};

export default TradingDashboard;
