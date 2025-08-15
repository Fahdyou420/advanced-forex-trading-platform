import React, { useState, useEffect, useRef } from 'react';

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

  // Fetch initial data
  const fetchInitialData = async () => {
    try {
      // Mock data for initial display
      setPrices({
        EURUSD: { price: 1.0850, bid: 1.0849, ask: 1.0851, spread: 0.0002 },
        GBPUSD: { price: 1.2720, bid: 1.2719, ask: 1.2721, spread: 0.0002 },
        USDJPY: { price: 149.50, bid: 149.48, ask: 149.52, spread: 0.04 }
      });

      setPerformance({
        strategies: [
          { name: 'breakout', performance_score: 0.75, total_trades: 15, avg_pnl: 25.50 },
          { name: 'support_resistance', performance_score: 0.68, total_trades: 12, avg_pnl: 18.30 }
        ],
        overall: {
          total_trades: 27,
          win_rate: 72.5,
          total_pnl: 430.50,
          avg_pnl: 15.94
        }
      });

      setSignals([
        {
          id: '1',
          strategy_name: 'breakout',
          pair: 'EURUSD',
          signal_type: 'BUY',
          entry_price: 1.0850,
          stop_loss: 1.0830,
          take_profit: 1.0890,
          confidence: 0.85,
          created_at: new Date().toISOString()
        }
      ]);

    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, []);

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
            <div className="bg-green-900 text-green-400 px-4 py-2 rounded-lg">
              <span className="text-sm font-medium">CONNECTED</span>
            </div>
            <div className="bg-blue-900 text-blue-400 px-4 py-2 rounded-lg">
              <span className="text-sm font-medium">PAPER MODE</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Live Prices */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4 text-blue-400">Live Prices</h2>
          <div className="space-y-3">
            {Object.entries(prices).map(([pair, priceData]) => (
              <div key={pair} className="flex justify-between items-center p-3 rounded bg-gray-700">
                <div>
                  <div className="font-semibold">{formatPair(pair)}</div>
                  <div className="text-xs text-gray-400">
                    Spread: {(priceData.spread * 10000).toFixed(1)} pips
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-lg text-green-400">
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

        {/* Recent Signals */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4 text-blue-400">Recent Signals</h2>
          <div className="space-y-3">
            {signals.map((signal, index) => (
              <div key={signal.id || index} className="p-4 rounded-lg border-l-4 border-green-400 bg-green-900/20">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <div className="font-semibold text-lg">
                      {formatPair(signal.pair)}
                      <span className="ml-2 px-2 py-1 text-xs rounded bg-green-600">
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
                    <div className="text-sm px-2 py-1 rounded bg-green-600">
                      {(signal.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-gray-400">SL</div>
                    <div className="font-mono">{formatPrice(signal.stop_loss, signal.pair)}</div>
                  </div>
                  <div>
                    <div className="text-gray-400">TP</div>
                    <div className="font-mono">{formatPrice(signal.take_profit, signal.pair)}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Performance */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4 text-blue-400">Performance</h2>
          <div className="grid grid-cols-2 gap-4 mb-6">
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
          </div>

          <div className="space-y-3">
            <h3 className="font-semibold text-gray-300">Strategy Performance</h3>
            {performance.strategies.map((strategy, index) => (
              <div key={strategy.name || index} className="bg-gray-700 p-3 rounded-lg">
                <div className="flex justify-between items-center">
                  <div className="font-semibold capitalize">
                    {strategy.name.replace(/_/g, ' ')}
                  </div>
                  <div className="px-2 py-1 rounded text-sm bg-green-600">
                    {((strategy.performance_score || 0) * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="text-sm text-gray-400">
                  {strategy.total_trades || 0} trades • ${(strategy.avg_pnl || 0).toFixed(2)} avg
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 text-center text-gray-500">
        <p>Forex Trading Platform v1.0 • Paper Trading Mode</p>
      </div>
    </div>
  );
};

export default TradingDashboard;
