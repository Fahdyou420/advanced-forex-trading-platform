"""
COMPLETE FOREX TRADING SIGNALS PLATFORM
Backend API using FastAPI with ExchangeRate API integration
Paper trading engine with dynamic strategy adaptation
Ready for Render deployment
"""

import os
import json
import logging
import asyncio
import time
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

import requests
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Configuration
EXCHANGERATE_API_KEY = os.getenv("EXCHANGERATE_API_KEY", "f2dfe9706f3c311136dd15b4")
API_SECRET = os.getenv("API_SECRET", "forex_2025_secure")
PAPER_MODE = os.getenv("PAPER_MODE", "true").lower() == "true"

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data Models
class Signal(BaseModel):
    strategy_name: str
    pair: str
    signal_type: str  # BUY, SELL
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    risk_reward_ratio: float

class Trade(BaseModel):
    signal_id: str
    strategy_name: str
    pair: str
    entry_price: float
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    status: str = "OPEN"  # OPEN, CLOSED, CANCELLED
    leverage: float = 1.0
    position_size: float = 1000.0

class StrategyPerformance(BaseModel):
    name: str
    win_rate: float
    avg_pnl: float
    max_drawdown: float
    total_trades: int
    performance_score: float

@dataclass
class MarketPrice:
    pair: str
    price: float
    timestamp: datetime
    bid: float
    ask: float
    spread: float

# Database Manager
class DatabaseManager:
    def __init__(self, db_path: str = "trading_platform.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with all required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Strategies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                performance_score REAL DEFAULT 0.5,
                win_rate REAL DEFAULT 0.0,
                avg_pnl REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                total_trades INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Signals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                pair TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                confidence REAL NOT NULL,
                risk_reward_ratio REAL NOT NULL,
                status TEXT DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                signal_id TEXT,
                strategy_name TEXT NOT NULL,
                pair TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                pnl REAL,
                status TEXT DEFAULT 'OPEN',
                leverage REAL DEFAULT 1.0,
                position_size REAL DEFAULT 1000.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                FOREIGN KEY (signal_id) REFERENCES signals (id)
            )
        """)
        
        # Market data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair TEXT NOT NULL,
                price REAL NOT NULL,
                bid REAL NOT NULL,
                ask REAL NOT NULL,
                spread REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                strategy_name TEXT PRIMARY KEY,
                win_rate REAL DEFAULT 0.0,
                avg_pnl REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                total_trades INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Initialize default strategies
        strategies = [
            ("breakout", "Breakout Strategy - Trades price breakouts above/below key levels"),
            ("support_resistance", "Support/Resistance Strategy - Trades bounces off key levels"),
            ("scalping", "Scalping Strategy - Quick profits from small price movements"),
            ("fibonacci_retracement", "Fibonacci Strategy - Trades retracements at Fibonacci levels"),
            ("range_trading", "Range Trading - Trades within established price ranges"),
            ("price_action", "Price Action Strategy - Pure price movement analysis")
        ]
        
        for name, desc in strategies:
            cursor.execute("""
                INSERT OR IGNORE INTO strategies (name, description) VALUES (?, ?)
            """, (name, desc))
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def execute_query(self, query: str, params: tuple = ()):
        """Execute a database query"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.commit()
        conn.close()
        return result
    
    def save_signal(self, signal: Signal) -> str:
        """Save a trading signal"""
        signal_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signals (id, strategy_name, pair, signal_type, entry_price, 
                               stop_loss, take_profit, confidence, risk_reward_ratio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (signal_id, signal.strategy_name, signal.pair, signal.signal_type,
              signal.entry_price, signal.stop_loss, signal.take_profit,
              signal.confidence, signal.risk_reward_ratio))
        conn.commit()
        conn.close()
        return signal_id
    
    def save_trade(self, trade: Trade) -> str:
        """Save a trade"""
        trade_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trades (id, signal_id, strategy_name, pair, entry_price,
                              exit_price, pnl, status, leverage, position_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (trade_id, trade.signal_id, trade.strategy_name, trade.pair,
              trade.entry_price, trade.exit_price, trade.pnl, trade.status,
              trade.leverage, trade.position_size))
        conn.commit()
        conn.close()
        return trade_id

# ExchangeRate API Manager
class ExchangeRateAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://v6.exchangerate-api.com/v6"
        self.cache = {}
        self.cache_ttl = 60  # 1 minute cache
    
    async def get_exchange_rates(self, base_currency: str = "USD") -> Dict:
        """Get exchange rates from ExchangeRate API"""
        cache_key = f"rates_{base_currency}"
        now = time.time()
        
        # Check cache
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if now - timestamp < self.cache_ttl:
                return data
        
        try:
            url = f"{self.base_url}/{self.api_key}/latest/{base_currency}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("result") == "success":
                self.cache[cache_key] = (data, now)
                return data
            else:
                logger.error(f"ExchangeRate API error: {data.get('error-type', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"Error fetching exchange rates: {e}")
            return {}
    
    async def get_forex_prices(self) -> Dict[str, MarketPrice]:
        """Convert exchange rates to forex prices"""
        rates_data = await self.get_exchange_rates("USD")
        
        if not rates_data or "conversion_rates" not in rates_data:
            return {}
        
        rates = rates_data["conversion_rates"]
        forex_pairs = {}
        
        # Major forex pairs
        pairs_mapping = {
            "EURUSD": ("EUR", "USD"),
            "GBPUSD": ("GBP", "USD"),
            "USDJPY": ("USD", "JPY"),
            "AUDUSD": ("AUD", "USD"),
            "USDCAD": ("USD", "CAD"),
            "USDCHF": ("USD", "CHF"),
            "NZDUSD": ("NZD", "USD"),
            "EURJPY": ("EUR", "JPY"),
            "GBPJPY": ("GBP", "JPY"),
            "AUDJPY": ("AUD", "JPY")
        }
        
        for pair, (base, quote) in pairs_mapping.items():
            try:
                if base == "USD" and quote in rates:
                    price = rates[quote]
                elif quote == "USD" and base in rates:
                    price = 1 / rates[base]
                elif base in rates and quote in rates:
                    price = rates[quote] / rates[base]
                else:
                    continue
                
                # Add realistic spread (0.1-0.3 pips for majors)
                spread = 0.00015 if not pair.endswith("JPY") else 0.015
                bid = price - spread / 2
                ask = price + spread / 2
                
                forex_pairs[pair] = MarketPrice(
                    pair=pair,
                    price=round(price, 5),
                    timestamp=datetime.now(timezone.utc),
                    bid=round(bid, 5),
                    ask=round(ask, 5),
                    spread=spread
                )
                
            except Exception as e:
                logger.error(f"Error calculating price for {pair}: {e}")
                continue
        
        return forex_pairs

# Trading Strategies
class TradingStrategies:
    def __init__(self):
        self.min_confidence = 0.6
    
    def calculate_technical_indicators(self, prices: List[float]) -> Dict:
        """Calculate basic technical indicators"""
        if len(prices) < 20:
            return {}
        
        df = pd.DataFrame(prices, columns=['close'])
        
        # Simple Moving Averages
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(min(50, len(prices))).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        bb_period = min(20, len(prices))
        bb_std = df['close'].rolling(bb_period).std()
        df['bb_upper'] = df['sma_20'] + (bb_std * 2)
        df['bb_lower'] = df['sma_20'] - (bb_std * 2)
        
        return df.iloc[-1].to_dict()
    
    def breakout_strategy(self, pair: str, current_price: float, historical_prices: List[float]) -> Optional[Signal]:
        """Breakout strategy implementation"""
        if len(historical_prices) < 20:
            return None
        
        indicators = self.calculate_technical_indicators(historical_prices)
        if not indicators:
            return None
        
        # Look for breakout above resistance or below support
        recent_high = max(historical_prices[-10:])
        recent_low = min(historical_prices[-10:])
        
        signal_type = None
        confidence = 0.5
        
        # Bullish breakout
        if current_price > recent_high and indicators.get('rsi', 50) < 70:
            signal_type = "BUY"
            confidence = min(0.85, 0.6 + (current_price - recent_high) / recent_high)
            entry_price = current_price
            stop_loss = recent_high * 0.999  # 0.1% below breakout level
            take_profit = current_price * 1.015  # 1.5% target
        
        # Bearish breakout
        elif current_price < recent_low and indicators.get('rsi', 50) > 30:
            signal_type = "SELL"
            confidence = min(0.85, 0.6 + (recent_low - current_price) / recent_low)
            entry_price = current_price
            stop_loss = recent_low * 1.001  # 0.1% above breakout level
            take_profit = current_price * 0.985  # 1.5% target
        
        if signal_type and confidence >= self.min_confidence:
            risk_reward = abs(take_profit - entry_price) / abs(stop_loss - entry_price)
            
            return Signal(
                strategy_name="breakout",
                pair=pair,
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=confidence,
                risk_reward_ratio=risk_reward
            )
        
        return None
    
    def support_resistance_strategy(self, pair: str, current_price: float, historical_prices: List[float]) -> Optional[Signal]:
        """Support/Resistance strategy implementation"""
        if len(historical_prices) < 20:
            return None
        
        indicators = self.calculate_technical_indicators(historical_prices)
        if not indicators:
            return None
        
        # Calculate support and resistance levels
        recent_prices = historical_prices[-20:]
        support = min(recent_prices)
        resistance = max(recent_prices)
        
        signal_type = None
        confidence = 0.5
        
        # Bounce off support
        if abs(current_price - support) / support < 0.002 and indicators.get('rsi', 50) < 40:
            signal_type = "BUY"
            confidence = 0.75
            entry_price = current_price
            stop_loss = support * 0.998
            take_profit = support + (resistance - support) * 0.6
        
        # Bounce off resistance
        elif abs(current_price - resistance) / resistance < 0.002 and indicators.get('rsi', 50) > 60:
            signal_type = "SELL"
            confidence = 0.75
            entry_price = current_price
            stop_loss = resistance * 1.002
            take_profit = resistance - (resistance - support) * 0.6
        
        if signal_type and confidence >= self.min_confidence:
            risk_reward = abs(take_profit - entry_price) / abs(stop_loss - entry_price)
            
            return Signal(
                strategy_name="support_resistance",
                pair=pair,
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=confidence,
                risk_reward_ratio=risk_reward
            )
        
        return None
    
    def scalping_strategy(self, pair: str, current_price: float, historical_prices: List[float]) -> Optional[Signal]:
        """Scalping strategy for quick profits"""
        if len(historical_prices) < 10:
            return None
        
        indicators = self.calculate_technical_indicators(historical_prices)
        if not indicators:
            return None
        
        # Quick scalping signals based on short-term momentum
        recent_prices = historical_prices[-5:]
        price_change = (current_price - recent_prices[0]) / recent_prices[0]
        
        signal_type = None
        confidence = 0.5
        
        # Quick up move
        if price_change > 0.001 and indicators.get('rsi', 50) < 65:
            signal_type = "BUY"
            confidence = 0.7
            entry_price = current_price
            stop_loss = current_price * 0.9995  # Tight 5 pip stop
            take_profit = current_price * 1.0008  # 8 pip target
        
        # Quick down move
        elif price_change < -0.001 and indicators.get('rsi', 50) > 35:
            signal_type = "SELL"
            confidence = 0.7
            entry_price = current_price
            stop_loss = current_price * 1.0005  # Tight 5 pip stop
            take_profit = current_price * 0.9992  # 8 pip target
        
        if signal_type and confidence >= self.min_confidence:
            risk_reward = abs(take_profit - entry_price) / abs(stop_loss - entry_price)
            
            return Signal(
                strategy_name="scalping",
                pair=pair,
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=confidence,
                risk_reward_ratio=risk_reward
            )
        
        return None
    
    def fibonacci_strategy(self, pair: str, current_price: float, historical_prices: List[float]) -> Optional[Signal]:
        """Fibonacci retracement strategy"""
        if len(historical_prices) < 30:
            return None
        
        # Find swing high and low
        recent_prices = historical_prices[-20:]
        swing_high = max(recent_prices)
        swing_low = min(recent_prices)
        
        # Calculate Fibonacci levels
        diff = swing_high - swing_low
        fib_618 = swing_high - (diff * 0.618)
        fib_382 = swing_high - (diff * 0.382)
        
        signal_type = None
        confidence = 0.5
        
        # Buy at 61.8% retracement
        if abs(current_price - fib_618) / current_price < 0.001:
            signal_type = "BUY"
            confidence = 0.72
            entry_price = current_price
            stop_loss = swing_low * 0.999
            take_profit = swing_high * 0.95
        
        # Buy at 38.2% retracement (weaker signal)
        elif abs(current_price - fib_382) / current_price < 0.001:
            signal_type = "BUY"
            confidence = 0.65
            entry_price = current_price
            stop_loss = fib_618 * 0.999
            take_profit = swing_high * 0.9
        
        if signal_type and confidence >= self.min_confidence:
            risk_reward = abs(take_profit - entry_price) / abs(stop_loss - entry_price)
            
            return Signal(
                strategy_name="fibonacci_retracement",
                pair=pair,
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=confidence,
                risk_reward_ratio=risk_reward
            )
        
        return None
    
    def range_trading_strategy(self, pair: str, current_price: float, historical_prices: List[float]) -> Optional[Signal]:
        """Range trading strategy"""
        if len(historical_prices) < 30:
            return None
        
        # Identify range
        recent_prices = historical_prices[-25:]
        range_high = max(recent_prices)
        range_low = min(recent_prices)
        range_size = range_high - range_low
        
        # Only trade if in a clear range
        if range_size / current_price < 0.01:  # Range less than 1%
            return None
        
        signal_type = None
        confidence = 0.5
        
        # Buy near range low
        if current_price <= range_low + (range_size * 0.2):
            signal_type = "BUY"
            confidence = 0.68
            entry_price = current_price
            stop_loss = range_low * 0.999
            take_profit = range_high * 0.95
        
        # Sell near range high
        elif current_price >= range_high - (range_size * 0.2):
            signal_type = "SELL"
            confidence = 0.68
            entry_price = current_price
            stop_loss = range_high * 1.001
            take_profit = range_low * 1.05
        
        if signal_type and confidence >= self.min_confidence:
            risk_reward = abs(take_profit - entry_price) / abs(stop_loss - entry_price)
            
            return Signal(
                strategy_name="range_trading",
                pair=pair,
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=confidence,
                risk_reward_ratio=risk_reward
            )
        
        return None
    
    def price_action_strategy(self, pair: str, current_price: float, historical_prices: List[float]) -> Optional[Signal]:
        """Price action strategy"""
        if len(historical_prices) < 15:
            return None
        
        # Look for price action patterns
        recent_prices = historical_prices[-10:]
        
        # Bullish engulfing pattern
        if len(recent_prices) >= 2:
            prev_price = recent_prices[-2]
            if current_price > prev_price * 1.002:  # Strong bullish move
                signal_type = "BUY"
                confidence = 0.71
                entry_price = current_price
                stop_loss = prev_price * 0.998
                take_profit = current_price * 1.01
                
                risk_reward = abs(take_profit - entry_price) / abs(stop_loss - entry_price)
                
                if confidence >= self.min_confidence:
                    return Signal(
                        strategy_name="price_action",
                        pair=pair,
                        signal_type=signal_type,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        confidence=confidence,
                        risk_reward_ratio=risk_reward
                    )
        
        return None

# Paper Trading Engine
class PaperTradingEngine:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.default_balance = 10000.0
        self.default_leverage = 1.0
    
    def execute_signal(self, signal: Signal, balance: float = None) -> str:
        """Execute a signal as a paper trade"""
        if balance is None:
            balance = self.default_balance
        
        # Calculate position size (2% risk per trade)
        risk_amount = balance * 0.02
        pip_value = 1.0  # Simplified
        
        if signal.pair.endswith("JPY"):
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        stop_distance = abs(signal.entry_price - signal.stop_loss)
        position_size = min(balance * 0.1, risk_amount / stop_distance)  # Max 10% of balance
        
        trade = Trade(
            signal_id=str(uuid.uuid4()),
            strategy_name=signal.strategy_name,
            pair=signal.pair,
            entry_price=signal.entry_price,
            status="OPEN",
            leverage=self.default_leverage,
            position_size=position_size
        )
        
        trade_id = self.db.save_trade(trade)
        logger.info(f"Paper trade executed: {signal.pair} {signal.signal_type} @ {signal.entry_price}")
        
        return trade_id
    
    def check_trade_exits(self, current_prices: Dict[str, MarketPrice]):
        """Check and close trades based on current prices"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Get open trades
        cursor.execute("SELECT * FROM trades WHERE status = 'OPEN'")
        open_trades = cursor.fetchall()
        
        for trade_row in open_trades:
            trade_id, signal_id, strategy_name, pair, entry_price, exit_price, pnl, status, leverage, position_size, created_at, closed_at = trade_row
            
            if pair not in current_prices:
                continue
            
            current_price = current_prices[pair].price
            
            # Get signal for SL/TP levels
            cursor.execute("SELECT stop_loss, take_profit, signal_type FROM signals WHERE id = ?", (signal_id,))
            signal_data = cursor.fetchone()
            
            if not signal_data:
                continue
            
            stop_loss, take_profit, signal_type = signal_data
            
            # Check exit conditions
            exit_reason = None
            
            if signal_type == "BUY":
                if current_price <= stop_loss:
                    exit_reason = "STOP_LOSS"
                elif current_price >= take_profit:
                    exit_reason = "TAKE_PROFIT"
            else:  # SELL
                if current_price >= stop_loss:
                    exit_reason = "STOP_LOSS"
                elif current_price <= take_profit:
                    exit_reason = "TAKE_PROFIT"
            
            if exit_reason:
                # Calculate PnL
                if signal_type == "BUY":
                    trade_pnl = (current_price - entry_price) * position_size
                else:
                    trade_pnl = (entry_price - current_price) * position_size
                
                # Close the trade
                cursor.execute("""
                    UPDATE trades 
                    SET exit_price = ?, pnl = ?, status = ?, closed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (current_price, trade_pnl, "CLOSED", trade_id))
                
                logger.info(f"Trade closed: {pair} {signal_type} PnL: ${trade_pnl:.2f} ({exit_reason})")
        
        conn.commit()
        conn.close()

# Dynamic Strategy Selector
class DynamicStrategySelector:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def update_strategy_performance(self):
        """Update performance metrics for all strategies"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Get all strategies
        cursor.execute("SELECT name FROM strategies")
        strategies = cursor.fetchall()
        
        for (strategy_name,) in strategies:
            # Calculate performance metrics
            cursor.execute("""
                SELECT COUNT(*) as total_trades,
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                       AVG(pnl) as avg_pnl,
                       MIN(pnl) as max_loss
                FROM trades 
                WHERE strategy_name = ? AND status = 'CLOSED'
                AND created_at >= datetime('now', '-30 days')
            """, (strategy_name,))
            
            result = cursor.fetchone()
            total_trades, winning_trades, avg_pnl, max_loss = result
            
            if total_trades and total_trades > 0:
                win_rate = (winning_trades or 0) / total_trades
                avg_pnl = avg_pnl or 0
                max_drawdown = abs(max_loss or 0)
                
                # Calculate performance score (0-1)
                performance_score = (
                    win_rate * 0.4 +  # 40% weight on win rate
                    min(1.0, max(0, (avg_pnl + 50) / 100)) * 0.4 +  # 40% weight on avg PnL
                    max(0, 1 - max_drawdown / 200) * 0.2  # 20% weight on drawdown
                )
                
                # Update strategy
                cursor.execute("""
                    UPDATE strategies 
                    SET performance_score = ?, win_rate = ?, avg_pnl = ?, 
                        max_drawdown = ?, total_trades = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE name = ?
                """, (performance_score, win_rate, avg_pnl, max_drawdown, total_trades, strategy_name))
                
                # Update performance metrics table
                cursor.execute("""
                    INSERT OR REPLACE INTO performance_metrics 
                    (strategy_name, win_rate, avg_pnl, max_drawdown, total_trades, last_updated)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (strategy_name, win_rate, avg_pnl, max_drawdown, total_trades))
        
        conn.commit()
        conn.close()
        
        logger.info("Strategy performance updated")
    
    def get_best_strategies(self, limit: int = 3) -> List[str]:
        """Get the best performing strategies"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM strategies 
            WHERE total_trades >= 5  -- Only strategies with enough trades
            ORDER BY performance_score DESC 
            LIMIT ?
        """, (limit,))
        
        strategies = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # If no strategies have enough trades, return all
        if not strategies:
            cursor = sqlite3.connect(self.db.db_path).cursor()
            cursor.execute("SELECT name FROM strategies ORDER BY performance_score DESC LIMIT ?", (limit,))
            strategies = [row[0] for row in cursor.fetchall()]
            cursor.connection.close()
        
        return strategies

# Main Trading Platform
class TradingPlatform:
    def __init__(self):
        self.db = DatabaseManager()
        self.exchange_api = ExchangeRateAPI(EXCHANGERATE_API_KEY)
        self.strategies = TradingStrategies()
        self.paper_engine = PaperTradingEngine(self.db)
        self.strategy_selector = DynamicStrategySelector(self.db)
        self.current_prices = {}
        self.price_history = {}
        self.connected_websockets = []
    
    async def fetch_market_data(self):
        """Fetch and store market data"""
        try:
            prices = await self.exchange_api.get_forex_prices()
            
            if not prices:
                logger.warning("No price data received")
                return
            
            self.current_prices = prices
            
            # Store in database and update price history
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            for pair, price_data in prices.items():
                cursor.execute("""
                    INSERT INTO market_data (pair, price, bid, ask, spread)
                    VALUES (?, ?, ?, ?, ?)
                """, (pair, price_data.price, price_data.bid, price_data.ask, price_data.spread))
                
                # Update price history
                if pair not in self.price_history:
                    self.price_history[pair] = []
                
                self.price_history[pair].append(price_data.price)
                
                # Keep only last 100 prices
                if len(self.price_history[pair]) > 100:
                    self.price_history[pair] = self.price_history[pair][-100:]
            
            conn.commit()
            conn.close()
            
            # Broadcast to WebSocket clients
            await self.broadcast_price_update(prices)
            
            logger.info(f"Updated prices for {len(prices)} pairs")
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
    
    async def generate_signals(self):
        """Generate trading signals using all strategies"""
        if not self.current_prices or not self.price_history:
            logger.warning("No price data available for signal generation")
            return
        
        new_signals = []
        
        # Get best performing strategies
        best_strategies = self.strategy_selector.get_best_strategies()
        
        for pair, price_data in self.current_prices.items():
            if pair not in self.price_history or len(self.price_history[pair]) < 10:
                continue
            
            current_price = price_data.price
            historical_prices = self.price_history[pair]
            
            # Run all strategy methods
            strategy_methods = [
                self.strategies.breakout_strategy,
                self.strategies.support_resistance_strategy,
                self.strategies.scalping_strategy,
                self.strategies.fibonacci_strategy,
                self.strategies.range_trading_strategy,
                self.strategies.price_action_strategy
            ]
            
            for strategy_method in strategy_methods:
                try:
                    signal = strategy_method(pair, current_price, historical_prices)
                    
                    if signal and signal.strategy_name in best_strategies:
                        # Boost confidence for best performing strategies
                        signal.confidence = min(0.95, signal.confidence * 1.1)
                    
                    if signal and signal.confidence >= 0.6:
                        signal_id = self.db.save_signal(signal)
                        new_signals.append(signal)
                        
                        # Auto-execute in paper mode
                        if PAPER_MODE:
                            self.paper_engine.execute_signal(signal)
                        
                        logger.info(f"New signal: {signal.strategy_name} {signal.pair} {signal.signal_type} @ {signal.entry_price}")
                
                except Exception as e:
                    logger.error(f"Error in strategy {strategy_method.__name__}: {e}")
        
        # Broadcast new signals
        if new_signals:
            await self.broadcast_signals(new_signals)
        
        return new_signals
    
    async def update_trades(self):
        """Update open trades and check for exits"""
        if not self.current_prices:
            return
        
        try:
            self.paper_engine.check_trade_exits(self.current_prices)
            
            # Update strategy performance
            self.strategy_selector.update_strategy_performance()
            
        except Exception as e:
            logger.error(f"Error updating trades: {e}")
    
    async def broadcast_price_update(self, prices: Dict[str, MarketPrice]):
        """Broadcast price updates to WebSocket clients"""
        if not self.connected_websockets:
            return
        
        message = {
            "type": "price_update",
            "data": {
                pair: {
                    "price": price_data.price,
                    "bid": price_data.bid,
                    "ask": price_data.ask,
                    "spread": price_data.spread,
                    "timestamp": price_data.timestamp.isoformat()
                }
                for pair, price_data in prices.items()
            }
        }
        
        # Send to all connected clients
        for websocket in self.connected_websockets[:]:
            try:
                await websocket.send_text(json.dumps(message))
            except:
                self.connected_websockets.remove(websocket)
    
    async def broadcast_signals(self, signals: List[Signal]):
        """Broadcast new signals to WebSocket clients"""
        if not self.connected_websockets:
            return
        
        message = {
            "type": "new_signals",
            "data": [
                {
                    "strategy_name": signal.strategy_name,
                    "pair": signal.pair,
                    "signal_type": signal.signal_type,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "confidence": signal.confidence,
                    "risk_reward_ratio": signal.risk_reward_ratio
                }
                for signal in signals
            ]
        }
        
        for websocket in self.connected_websockets[:]:
            try:
                await websocket.send_text(json.dumps(message))
            except:
                self.connected_websockets.remove(websocket)

# Initialize the trading platform
trading_platform = TradingPlatform()

# FastAPI Application
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background tasks
    async def market_data_loop():
        while True:
            await trading_platform.fetch_market_data()
            await asyncio.sleep(30)  # Update every 30 seconds
    
    async def signal_generation_loop():
        while True:
            await trading_platform.generate_signals()
            await asyncio.sleep(60)  # Generate signals every minute
    
    async def trade_update_loop():
        while True:
            await trading_platform.update_trades()
            await asyncio.sleep(30)  # Update trades every 30 seconds
    
    # Start background tasks
    market_task = asyncio.create_task(market_data_loop())
    signal_task = asyncio.create_task(signal_generation_loop())
    trade_task = asyncio.create_task(trade_update_loop())
    
    yield
    
    # Cleanup
    market_task.cancel()
    signal_task.cancel()
    trade_task.cancel()

app = FastAPI(
    title="Forex Trading Platform",
    description="Complete trading platform with signals, paper trading, and automation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# API Endpoints
@app.get("/")
async def root():
    return {
        "service": "Forex Trading Platform",
        "version": "1.0.0",
        "status": "running",
        "paper_mode": PAPER_MODE,
        "features": [
            "Real-time forex prices via ExchangeRate API",
            "6 trading strategies with dynamic adaptation",
            "Paper trading engine",
            "WebSocket real-time updates",
            "Performance tracking and optimization"
        ]
    }

@app.get("/health")
async def health_check():
    try:
        # Test database connection
        conn = sqlite3.connect(trading_platform.db.db_path)
        conn.close()
        
        # Test API connection
        test_data = await trading_platform.exchange_api.get_exchange_rates()
        api_status = "connected" if test_data else "disconnected"
        
        return {
            "status": "healthy",
            "database": "connected",
            "exchange_api": api_status,
            "paper_mode": PAPER_MODE,
            "active_pairs": len(trading_platform.current_prices),
            "websocket_connections": len(trading_platform.connected_websockets)
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/prices")
async def get_current_prices():
    """Get current market prices"""
    return {
        "prices": {
            pair: {
                "price": price_data.price,
                "bid": price_data.bid,
                "ask": price_data.ask,
                "spread": price_data.spread,
                "timestamp": price_data.timestamp.isoformat()
            }
            for pair, price_data in trading_platform.current_prices.items()
        }
    }

@app.get("/signals")
async def get_recent_signals(limit: int = 20):
    """Get recent trading signals"""
    conn = sqlite3.connect(trading_platform.db.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM signals 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    
    columns = [desc[0] for desc in cursor.description]
    signals = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return {"signals": signals}

@app.get("/trades")
async def get_trades(status: str = None, limit: int = 50):
    """Get trading history"""
    conn = sqlite3.connect(trading_platform.db.db_path)
    cursor = conn.cursor()
    
    if status:
        cursor.execute("""
            SELECT * FROM trades 
            WHERE status = ?
            ORDER BY created_at DESC 
            LIMIT ?
        """, (status, limit))
    else:
        cursor.execute("""
            SELECT * FROM trades 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
    
    columns = [desc[0] for desc in cursor.description]
    trades = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return {"trades": trades}

@app.get("/performance")
async def get_performance_metrics():
    """Get strategy performance metrics"""
    conn = sqlite3.connect(trading_platform.db.db_path)
    cursor = conn.cursor()
    
    # Strategy performance
    cursor.execute("""
        SELECT s.name, s.performance_score, s.win_rate, s.avg_pnl, 
               s.max_drawdown, s.total_trades
        FROM strategies s
        ORDER BY s.performance_score DESC
    """)
    
    columns = [desc[0] for desc in cursor.description]
    strategies = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # Overall performance
    cursor.execute("""
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
            AVG(pnl) as avg_pnl,
            SUM(pnl) as total_pnl,
            MIN(pnl) as worst_trade,
            MAX(pnl) as best_trade
        FROM trades 
        WHERE status = 'CLOSED'
    """)
    
    overall_stats = cursor.fetchone()
    
    conn.close()
    
    total_trades, winning_trades, avg_pnl, total_pnl, worst_trade, best_trade = overall_stats
    
    return {
        "strategies": strategies,
        "overall": {
            "total_trades": total_trades or 0,
            "winning_trades": winning_trades or 0,
            "win_rate": (winning_trades / total_trades * 100) if total_trades else 0,
            "avg_pnl": avg_pnl or 0,
            "total_pnl": total_pnl or 0,
            "worst_trade": worst_trade or 0,
            "best_trade": best_trade or 0
        }
    }

@app.post("/signals/manual")
async def create_manual_signal(signal: Signal, _: bool = Depends(verify_api_key)):
    """Create a manual trading signal"""
    signal_id = trading_platform.db.save_signal(signal)
    
    if PAPER_MODE:
        trade_id = trading_platform.paper_engine.execute_signal(signal)
        return {"signal_id": signal_id, "trade_id": trade_id, "status": "executed"}
    
    return {"signal_id": signal_id, "status": "created"}

@app.post("/webhook/n8n")
async def n8n_webhook(data: dict):
    """Webhook endpoint for N8N integration"""
    logger.info(f"N8N webhook received: {data}")
    
    # Process webhook data from N8N
    action = data.get("action")
    
    if action == "get_signals":
        # Return recent signals for N8N
        conn = sqlite3.connect(trading_platform.db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM signals 
            WHERE created_at >= datetime('now', '-1 hour')
            ORDER BY created_at DESC
        """)
        
        columns = [desc[0] for desc in cursor.description]
        recent_signals = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        
        return {"signals": recent_signals}
    
    elif action == "get_trades":
        # Return recent trades for N8N
        conn = sqlite3.connect(trading_platform.db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM trades 
            WHERE created_at >= datetime('now', '-1 hour')
            ORDER BY created_at DESC
        """)
        
        columns = [desc[0] for desc in cursor.description]
        recent_trades = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        
        return {"trades": recent_trades}
    
    return {"status": "received", "timestamp": datetime.now().isoformat()}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    trading_platform.connected_websockets.append(websocket)
    
    try:
        # Send initial data
        if trading_platform.current_prices:
            await websocket.send_text(json.dumps({
                "type": "price_update",
                "data": {
                    pair: {
                        "price": price_data.price,
                        "bid": price_data.bid,
                        "ask": price_data.ask,
                        "spread": price_data.spread,
                        "timestamp": price_data.timestamp.isoformat()
                    }
                    for pair, price_data in trading_platform.current_prices.items()
                }
            }))
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        if websocket in trading_platform.connected_websockets:
            trading_platform.connected_websockets.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
