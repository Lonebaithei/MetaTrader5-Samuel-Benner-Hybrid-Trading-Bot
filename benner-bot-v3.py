"""
MetaTrader 5 - Benner-Adjusted Hybrid Trading Strategy v3.0
ENTERPRISE EDITION - Production Ready

Author: Strategic Trading System
Date: January 2026
Version: 3.0 - Complete rewrite with all critical fixes

NEW FEATURES v3.0:
✓ Environment-based configuration (no hardcoded passwords)
✓ Weekend trading prevention
✓ Total exposure management
✓ Correlation risk management
✓ Performance tracking with win rate
✓ Telegram alerts
✓ Trade journal (CSV export)
✓ Dry-run mode for safe testing
✓ Log rotation
✓ Trailing stops
✓ Enhanced error handling
✓ Risk management dashboard
✓ Comprehensive test suite

REQUIREMENTS:
pip install MetaTrader5 pandas numpy yfinance python-dotenv requests
pip install pytest  # For testing
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import time
import logging
from logging.handlers import RotatingFileHandler
import sys
import os
import json
import csv
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("WARNING: python-dotenv not installed. Using defaults.")

# External APIs
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Trading Strategy Configuration"""

    # MT5 Connection (FROM ENVIRONMENT VARIABLES)
    MT5_LOGIN = int(os.getenv('MT5_LOGIN', '0'))
    MT5_PASSWORD = os.getenv('MT5_PASSWORD', '')
    MT5_SERVER = os.getenv('MT5_SERVER', 'Deriv-Demo')

    # Trading Mode
    DRY_RUN = os.getenv('DRY_RUN', 'True').lower() == 'true'  # Safe default
    
    # Trading Symbols
    SYMBOLS = {
        'mean_reversion': ['EURUSD', 'USDJPY', 'AUDUSD', 'XAUUSD'],
        'momentum': ['EURUSD', 'XAUUSD'],
        'defensive': ['XAUUSD', 'USDCHF']
    }
    
    # Symbol Correlation Matrix (to avoid over-exposure)
    CORRELATION_THRESHOLD = 0.70
    CORRELATIONS = {
        ('EURUSD', 'GBPUSD'): 0.80,
        ('EURUSD', 'AUDUSD'): 0.75,
        ('GBPUSD', 'AUDUSD'): 0.70,
    }

    # Benner Cycle Calendar
    BENNER_CALENDAR = {
        'Jan-2026': {'allocation': 0.50, 'phase': 'Selective Accumulation'},
        'Feb-2026': {'allocation': 0.60, 'phase': 'Build Positions'},
        'Mar-2026': {'allocation': 0.75, 'phase': 'Active Trading'},
        'Apr-2026': {'allocation': 0.60, 'phase': 'Take Profits'},
        'May-2026': {'allocation': 0.40, 'phase': 'Exit Mode'},
        'Jun-2026': {'allocation': 0.20, 'phase': 'Defensive'}
    }

    # Risk Management
    MAX_POSITION_SIZE_PCT = 0.02  # 2% risk per trade
    MAX_TOTAL_EXPOSURE_PCT = 0.30  # 30% total exposure
    STOP_LOSS_PIPS = 50
    TAKE_PROFIT_PIPS = 100
    TRAILING_STOP_PIPS = 30  # NEW: Trailing stop distance
    
    # Signal Filters
    RSI_BUY_THRESHOLD = 40  # Only buy if RSI below this
    REQUIRE_200MA_FILTER = True  # Require price above 200MA for buys

    # Technical Indicators
    BB_PERIOD = 20
    BB_STD = 2
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    MA_FAST = 20
    MA_SLOW = 50
    MA_LONG = 200

    # Market Warning Levels
    VIX_WARNING = 20
    VIX_CRITICAL = 25
    SPX_SUPPORT = 6600

    # Trading Parameters
    MAGIC_MEAN_REVERSION = 123456
    MAGIC_MOMENTUM = 123457
    MAGIC_DEFENSIVE = 123458
    SLIPPAGE = 10
    UPDATE_INTERVAL = 300  # 5 minutes
    MIN_BARS_REQUIRED = 250

    # Market Data Settings
    USE_EXTERNAL_API = True
    MAX_DATA_AGE_HOURS = 48
    VIX_SYMBOLS = ['VIX', 'VIXC', 'VIX.F', 'VIX.IDX', '#VIX', 'VOLATILITY']
    SPX_SYMBOLS = ['SPX500', 'US500', 'SPX', 'SP500', '#SPX', 'US500.IDX']

    # Telegram Alerts (optional)
    TELEGRAM_ENABLED = os.getenv('TELEGRAM_ENABLED', 'False').lower() == 'true'
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

    # Logging
    LOG_FILE = 'benner_bot_v3.log'
    LOG_LEVEL = logging.INFO
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5
    
    # Trade Journal
    TRADE_JOURNAL_FILE = 'trade_journal.csv'
    PERFORMANCE_FILE = 'performance_stats.json'

    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []
        
        if cls.MT5_LOGIN == 0:
            errors.append("MT5_LOGIN not set in environment variables")
        if not cls.MT5_PASSWORD:
            errors.append("MT5_PASSWORD not set in environment variables")
        if not cls.MT5_SERVER:
            errors.append("MT5_SERVER not set in environment variables")
        
        if cls.TELEGRAM_ENABLED and (not cls.TELEGRAM_BOT_TOKEN or not cls.TELEGRAM_CHAT_ID):
            errors.append("Telegram enabled but TOKEN or CHAT_ID not set")
        
        return errors


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Setup logging with rotation"""
    # Rotating file handler
    file_handler = RotatingFileHandler(
        Config.LOG_FILE,
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(Config.LOG_LEVEL)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(Config.LOG_LEVEL)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Setup logger
    logger = logging.getLogger(__name__)
    logger.setLevel(Config.LOG_LEVEL)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging()


# ============================================================================
# ALERT SYSTEM
# ============================================================================

class AlertSystem:
    """Send alerts via Telegram"""
    
    def __init__(self):
        self.enabled = Config.TELEGRAM_ENABLED and REQUESTS_AVAILABLE
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        
        if Config.TELEGRAM_ENABLED and not REQUESTS_AVAILABLE:
            logger.warning("Telegram enabled but 'requests' not installed")
            self.enabled = False
    
    def send(self, message: str, priority: str = 'INFO'):
        """Send Telegram message"""
        if not self.enabled:
            return
        
        try:
            # Add emoji based on priority
            emoji = {
                'INFO': 'ℹ️',
                'SUCCESS': '✅',
                'WARNING': '⚠️',
                'ERROR': '❌',
                'TRADE': '💰'
            }.get(priority, 'ℹ️')
            
            formatted_message = f"{emoji} <b>{priority}</b>\n\n{message}"
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": formatted_message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                logger.debug(f"Telegram alert sent: {priority}")
            else:
                logger.warning(f"Telegram alert failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
    
    def send_trade_alert(self, action: str, symbol: str, lots: float, 
                        price: float, sl: float, tp: float, strategy: str):
        """Send trade execution alert"""
        message = (
            f"<b>{action} {symbol}</b>\n"
            f"Lots: {lots:.3f}\n"
            f"Entry: ${price:.5f}\n"
            f"SL: ${sl:.5f}\n"
            f"TP: ${tp:.5f}\n"
            f"Strategy: {strategy}"
        )
        self.send(message, 'TRADE')
    
    def send_close_alert(self, symbol: str, lots: float, profit: float, reason: str):
        """Send position close alert"""
        emoji = '🟢' if profit > 0 else '🔴'
        message = (
            f"{emoji} <b>CLOSED {symbol}</b>\n"
            f"Lots: {lots:.3f}\n"
            f"Profit: ${profit:.2f}\n"
            f"Reason: {reason}"
        )
        self.send(message, 'TRADE')


# ============================================================================
# PERFORMANCE TRACKER
# ============================================================================

class PerformanceTracker:
    """Track bot performance and statistics"""
    
    def __init__(self):
        self.trades = []
        self.daily_pnl = {}
        self.load_history()
    
    def load_history(self):
        """Load trade history from file"""
        try:
            if os.path.exists(Config.PERFORMANCE_FILE):
                with open(Config.PERFORMANCE_FILE, 'r') as f:
                    data = json.load(f)
                    self.trades = data.get('trades', [])
                    self.daily_pnl = data.get('daily_pnl', {})
                logger.info(f"Loaded {len(self.trades)} historical trades")
        except Exception as e:
            logger.error(f"Error loading performance history: {e}")
    
    def save_history(self):
        """Save trade history to file"""
        try:
            data = {
                'trades': self.trades,
                'daily_pnl': self.daily_pnl,
                'last_updated': datetime.now().isoformat()
            }
            with open(Config.PERFORMANCE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving performance history: {e}")
    
    def record_trade(self, symbol: str, action: str, lots: float, entry: float,
                    exit_price: float, profit: float, strategy: str, reason: str):
        """Record a completed trade"""
        trade = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'action': action,
            'lots': lots,
            'entry': entry,
            'exit': exit_price,
            'profit': profit,
            'profit_pct': (profit / (lots * entry * 100000)) * 100 if entry > 0 else 0,
            'strategy': strategy,
            'reason': reason
        }
        
        self.trades.append(trade)
        
        # Update daily P/L
        date = datetime.now().strftime('%Y-%m-%d')
        self.daily_pnl[date] = self.daily_pnl.get(date, 0) + profit
        
        # Save to CSV journal
        self._append_to_journal(trade)
        
        # Save to JSON
        self.save_history()
        
        # Calculate and log statistics
        self._log_statistics()
    
    def _append_to_journal(self, trade: Dict):
        """Append trade to CSV journal"""
        try:
            file_exists = os.path.exists(Config.TRADE_JOURNAL_FILE)
            
            with open(Config.TRADE_JOURNAL_FILE, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=trade.keys())
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(trade)
                
        except Exception as e:
            logger.error(f"Error writing to trade journal: {e}")
    
    def _log_statistics(self):
        """Calculate and log performance statistics"""
        if not self.trades:
            return
        
        total_trades = len(self.trades)
        wins = len([t for t in self.trades if t['profit'] > 0])
        losses = len([t for t in self.trades if t['profit'] < 0])
        
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(t['profit'] for t in self.trades)
        avg_win = np.mean([t['profit'] for t in self.trades if t['profit'] > 0]) if wins > 0 else 0
        avg_loss = np.mean([t['profit'] for t in self.trades if t['profit'] < 0]) if losses > 0 else 0
        
        profit_factor = abs(avg_win * wins / (avg_loss * losses)) if losses > 0 and avg_loss != 0 else 0
        
        logger.info(f"\n{'='*60}")
        logger.info(f"PERFORMANCE STATISTICS")
        logger.info(f"{'='*60}")
        logger.info(f"Total Trades: {total_trades}")
        logger.info(f"Wins: {wins} | Losses: {losses}")
        logger.info(f"Win Rate: {win_rate:.1f}%")
        logger.info(f"Total P/L: ${total_profit:.2f}")
        logger.info(f"Avg Win: ${avg_win:.2f} | Avg Loss: ${avg_loss:.2f}")
        logger.info(f"Profit Factor: {profit_factor:.2f}")
        logger.info(f"{'='*60}\n")
    
    def get_statistics(self) -> Dict:
        """Get current performance statistics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_profit': 0,
                'profit_factor': 0
            }
        
        total_trades = len(self.trades)
        wins = len([t for t in self.trades if t['profit'] > 0])
        losses = len([t for t in self.trades if t['profit'] < 0])
        
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        total_profit = sum(t['profit'] for t in self.trades)
        
        avg_win = np.mean([t['profit'] for t in self.trades if t['profit'] > 0]) if wins > 0 else 0
        avg_loss = np.mean([t['profit'] for t in self.trades if t['profit'] < 0]) if losses > 0 else 0
        profit_factor = abs(avg_win * wins / (avg_loss * losses)) if losses > 0 and avg_loss != 0 else 0
        
        return {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor
        }


# ============================================================================
# WEEKEND/MARKET HOURS CHECK
# ============================================================================

class MarketHours:
    """Check if market is open (Forex 24/5)"""
    
    @staticmethod
    def is_weekend() -> bool:
        """Check if it's weekend (market closed)"""
        now = datetime.now(timezone.utc)
        
        # Saturday (5) or Sunday before 22:00 (6)
        if now.weekday() == 5:  # Saturday
            return True
        
        if now.weekday() == 6:  # Sunday
            if now.hour < 22:  # Market opens Sunday 22:00 UTC
                return True
        
        # Friday after 22:00 UTC (market closes)
        if now.weekday() == 4 and now.hour >= 22:
            return True
        
        return False
    
    @staticmethod
    def next_open_time() -> datetime:
        """Calculate when market opens next"""
        now = datetime.now(timezone.utc)
        
        # If Friday after close or Saturday, next open is Sunday 22:00
        if (now.weekday() == 4 and now.hour >= 22) or now.weekday() == 5:
            days_until_sunday = (6 - now.weekday()) % 7
            next_open = now.replace(hour=22, minute=0, second=0, microsecond=0)
            next_open += timedelta(days=days_until_sunday)
            return next_open
        
        # If Sunday before 22:00
        if now.weekday() == 6 and now.hour < 22:
            return now.replace(hour=22, minute=0, second=0, microsecond=0)
        
        return now  # Market is open


# ============================================================================
# RISK MANAGER
# ============================================================================

class RiskManager:
    """Manage overall portfolio risk"""
    
    def __init__(self):
        self.max_exposure = Config.MAX_TOTAL_EXPOSURE_PCT
        self.correlation_threshold = Config.CORRELATION_THRESHOLD
    
    def check_total_exposure(self, current_exposure: float) -> bool:
        """Check if current exposure is within limits"""
        if current_exposure >= self.max_exposure:
            logger.warning(f"Portfolio at max exposure: {current_exposure*100:.1f}%")
            return False
        return True
    
    def is_correlated(self, symbol1: str, symbol2: str) -> bool:
        """Check if two symbols are highly correlated"""
        pair = tuple(sorted([symbol1, symbol2]))
        correlation = Config.CORRELATIONS.get(pair, 0)
        
        return correlation > self.correlation_threshold
    
    def check_correlation_risk(self, new_symbol: str) -> bool:
        """Check if opening new position creates correlation risk"""
        positions = mt5.positions_get()
        if not positions:
            return True  # No positions, no risk
        
        for pos in positions:
            if self.is_correlated(new_symbol, pos.symbol):
                logger.warning(
                    f"High correlation between {new_symbol} and {pos.symbol} "
                    f"({Config.CORRELATIONS.get(tuple(sorted([new_symbol, pos.symbol])), 0):.2f})"
                )
                return False
        
        return True
    
    def can_open_position(self, symbol: str, current_exposure: float) -> Tuple[bool, str]:
        """Comprehensive check if we can open a new position"""
        # Check exposure
        if not self.check_total_exposure(current_exposure):
            return False, f"Max exposure reached ({current_exposure*100:.1f}%)"
        
        # Check correlation
        if not self.check_correlation_risk(symbol):
            return False, f"High correlation risk with existing positions"
        
        # Check for duplicate
        positions = mt5.positions_get(symbol=symbol)
        if positions and len(positions) > 0:
            return False, f"Already have position in {symbol}"
        
        return True, "OK"


# ============================================================================
# TECHNICAL INDICATORS (unchanged from v2.3)
# ============================================================================

class TechnicalIndicators:
    """Calculate technical indicators for trading signals"""

    @staticmethod
    def bollinger_bands(data: pd.DataFrame, period: int = 20, std: int = 2) -> pd.DataFrame:
        data['bb_middle'] = data['close'].rolling(window=period).mean()
        data['bb_std'] = data['close'].rolling(window=period).std()
        data['bb_upper'] = data['bb_middle'] + (std * data['bb_std'])
        data['bb_lower'] = data['bb_middle'] - (std * data['bb_std'])
        return data

    @staticmethod
    def rsi(data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, 0.0001)
        data['rsi'] = 100 - (100 / (1 + rs))
        return data

    @staticmethod
    def moving_averages(data: pd.DataFrame, fast: int = 20, slow: int = 50, long: int = 200) -> pd.DataFrame:
        data['ma_fast'] = data['close'].rolling(window=fast).mean()
        data['ma_slow'] = data['close'].rolling(window=slow).mean()
        data['ma_200'] = data['close'].rolling(window=long).mean()
        return data

    @staticmethod
    def volume_analysis(data: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        data['volume_avg'] = data['tick_volume'].rolling(window=period).mean()
        data['volume_spike'] = data['tick_volume'] > (data['volume_avg'] * 2)
        return data


# ============================================================================
# MARKET DATA PROVIDER (same as v2.3 but with minor fixes)
# ============================================================================

class MarketDataProvider:
    """Fetch VIX and SPX data from MT5 or external APIs with caching"""
    
    def __init__(self):
        self._vix_symbol = None
        self._spx_symbol = None
        self._last_vix_value = 20.5
        self._last_spx_value = 6797.0
        self._last_update = None
        
        logger.info("[MARKET DATA] Initializing market data provider...")
        self._discover_symbols()
    
    def _discover_symbols(self):
        logger.info("[MARKET DATA] Discovering available market indicators...")
        
        for symbol in Config.VIX_SYMBOLS:
            try:
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 1)
                if rates is not None and len(rates) > 0:
                    self._vix_symbol = symbol
                    self._last_vix_value = rates[0]['close']
                    logger.info(f"[VIX] Found working symbol: {symbol} = {self._last_vix_value:.2f}")
                    break
            except Exception:
                continue
        
        if self._vix_symbol is None:
            logger.warning("[VIX] No MT5 symbol found - will use external API or default")
        
        for symbol in Config.SPX_SYMBOLS:
            try:
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 1)
                if rates is not None and len(rates) > 0:
                    self._spx_symbol = symbol
                    self._last_spx_value = rates[0]['close']
                    logger.info(f"[SPX] Found working symbol: {symbol} = {self._last_spx_value:.2f}")
                    break
            except Exception:
                continue
        
        if self._spx_symbol is None:
            logger.warning("[SPX] No MT5 symbol found - will use external API or default")
    
    def _validate_data_freshness(self, timestamp: int) -> bool:
        data_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - data_time).total_seconds() / 3600
        
        if age_hours > Config.MAX_DATA_AGE_HOURS:
            logger.warning(f"Data is {age_hours:.1f} hours old (max: {Config.MAX_DATA_AGE_HOURS})")
            return False
        
        return True
    
    def _get_from_mt5(self, symbol: str, name: str) -> Optional[float]:
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 1)
            
            if rates is not None and len(rates) > 0:
                if not self._validate_data_freshness(rates[0]['time']):
                    return None
                
                value = rates[0]['close']
                logger.debug(f"[{name}] MT5 data: {symbol} = {value:.2f}")
                return value
            
        except Exception as e:
            logger.debug(f"[{name}] MT5 fetch failed for {symbol}: {e}")
        
        return None
    
    def _get_from_yfinance(self) -> Dict[str, Optional[float]]:
        if not YFINANCE_AVAILABLE:
            return {'vix': None, 'spx': None}
        
        try:
            logger.info("[EXTERNAL API] Fetching data from Yahoo Finance...")
            
            vix_value = None
            try:
                vix_ticker = yf.Ticker("^VIX")
                vix_data = vix_ticker.history(period='1d')
                if not vix_data.empty:
                    vix_value = float(vix_data['Close'].iloc[-1])
                    logger.info(f"[VIX] Yahoo Finance: {vix_value:.2f}")
            except Exception as e:
                logger.warning(f"[VIX] Yahoo Finance fetch failed: {e}")
            
            spx_value = None
            try:
                spx_ticker = yf.Ticker("^GSPC")
                spx_data = spx_ticker.history(period='1d')
                if not spx_data.empty:
                    spx_value = float(spx_data['Close'].iloc[-1])
                    logger.info(f"[SPX] Yahoo Finance: {spx_value:.2f}")
            except Exception as e:
                logger.warning(f"[SPX] Yahoo Finance fetch failed: {e}")
            
            return {'vix': vix_value, 'spx': spx_value}
            
        except Exception as e:
            logger.error(f"[EXTERNAL API] Yahoo Finance error: {e}")
            return {'vix': None, 'spx': None}
    
    def get_market_indicators(self) -> Dict[str, any]:
        vix_value = self._last_vix_value
        spx_value = self._last_spx_value
        vix_source = 'CACHED'
        spx_source = 'CACHED'
        
        if self._vix_symbol:
            mt5_vix = self._get_from_mt5(self._vix_symbol, 'VIX')
            if mt5_vix is not None:
                vix_value = mt5_vix
                vix_source = f'MT5:{self._vix_symbol}'
            else:
                self._vix_symbol = None
        
        if self._spx_symbol:
            mt5_spx = self._get_from_mt5(self._spx_symbol, 'SPX')
            if mt5_spx is not None:
                spx_value = mt5_spx
                spx_source = f'MT5:{self._spx_symbol}'
            else:
                self._spx_symbol = None
        
        if self._vix_symbol is None or self._spx_symbol is None:
            self._discover_symbols()
        
        if Config.USE_EXTERNAL_API and (self._vix_symbol is None or self._spx_symbol is None):
            external_data = self._get_from_yfinance()
            
            if external_data['vix'] is not None and self._vix_symbol is None:
                vix_value = external_data['vix']
                vix_source = 'Yahoo Finance'
            
            if external_data['spx'] is not None and self._spx_symbol is None:
                spx_value = external_data['spx']
                spx_source = 'Yahoo Finance'
        
        self._last_vix_value = vix_value
        self._last_spx_value = spx_value
        self._last_update = datetime.now(timezone.utc)
        
        return {
            'vix': vix_value,
            'spx': spx_value,
            'vix_source': vix_source,
            'spx_source': spx_source,
            'last_update': self._last_update
        }


# The next artifact
# CONTINUATION OF BENNER BOT V3.0
# This is Part 2

# ============================================================================
# MARKET REGIME DETECTOR
# ============================================================================

class MarketRegime:
    """Detect current market regime and generate warnings"""

    def __init__(self):
        self.vix_level = 0
        self.spx_level = 0

    def detect_regime(self, vix: float, spx: float) -> Dict[str, str]:
        self.vix_level = vix
        self.spx_level = spx

        if vix > Config.VIX_CRITICAL:
            return {
                'regime': 'HIGH VOLATILITY',
                'action': 'DEFENSIVE',
                'allocation': 0.20,
                'message': 'VIX critical - Exit positions and raise cash'
            }
        elif spx < Config.SPX_SUPPORT:
            return {
                'regime': 'BREAKDOWN',
                'action': 'EXIT',
                'allocation': 0.20,
                'message': 'S&P broke support - Emergency exit mode'
            }
        elif vix > Config.VIX_WARNING:
            return {
                'regime': 'TRANSITIONAL',
                'action': 'CAUTIOUS',
                'allocation': 0.50,
                'message': 'VIX elevated - Use mean reversion primary'
            }
        else:
            return {
                'regime': 'NORMAL',
                'action': 'ACTIVE',
                'allocation': 0.75,
                'message': 'Normal conditions - Execute hybrid strategy'
            }

    def get_warnings(self) -> List[Dict[str, str]]:
        warnings = []

        if self.spx_level < Config.SPX_SUPPORT:
            warnings.append({
                'level': 'CRITICAL',
                'message': f'S&P 500 at {self.spx_level} - Below key support {Config.SPX_SUPPORT}'
            })

        if self.vix_level > Config.VIX_CRITICAL:
            warnings.append({
                'level': 'CRITICAL',
                'message': f'VIX at {self.vix_level} - Extreme volatility detected'
            })
        elif self.vix_level > Config.VIX_WARNING:
            warnings.append({
                'level': 'WARNING',
                'message': f'VIX at {self.vix_level} - Elevated volatility'
            })

        return warnings


# ============================================================================
# SIGNAL GENERATOR
# ============================================================================

class SignalGenerator:
    """Generate trading signals based on strategy rules"""

    def __init__(self):
        self.indicators = TechnicalIndicators()

    def calculate_sl_tp_pips(self, symbol: str, price: float, is_buy: bool = True) -> Tuple[float, float]:
        """Calculate stop loss and take profit in price units based on pips"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                point = 0.00001 if 'JPY' not in symbol else 0.001
            else:
                point = symbol_info.point
            
            pip_value = point * 10
            
            if 'JPY' in symbol:
                pip_value = point * 100
            
            if symbol == 'XAUUSD':
                pip_value = 0.01
            
            sl_pips = Config.STOP_LOSS_PIPS
            tp_pips = Config.TAKE_PROFIT_PIPS
            
            if is_buy:
                sl_price = price - (sl_pips * pip_value)
                tp_price = price + (tp_pips * pip_value)
            else:
                sl_price = price + (sl_pips * pip_value)
                tp_price = price - (tp_pips * pip_value)
            
            return sl_price, tp_price
            
        except Exception as e:
            logger.error(f"Error calculating SL/TP for {symbol}: {e}")
            if is_buy:
                return price * 0.99, price * 1.02
            else:
                return price * 1.01, price * 0.98

    def mean_reversion_signal(self, data: pd.DataFrame, symbol: str) -> Dict[str, any]:
        """Mean Reversion Signal Logic"""
        if len(data) < Config.MA_LONG or data['ma_200'].isna().iloc[-1]:
            return {'signal': 'HOLD', 'reason': 'Insufficient data for 200-day MA'}

        latest = data.iloc[-1]

        if pd.isna(latest['bb_lower']) or pd.isna(latest['rsi']) or pd.isna(latest['ma_200']):
            return {'signal': 'HOLD', 'reason': 'Indicators not ready'}

        price_at_lower_bb = latest['close'] <= latest['bb_lower'] * 1.02
        rsi_oversold = latest['rsi'] < Config.RSI_OVERSOLD
        rsi_moderately_oversold = latest['rsi'] < 45
        above_200ma = latest['close'] > latest['ma_200']
        volume_spike = latest.get('volume_spike', False)

        price_at_middle = latest['close'] >= latest['bb_middle']
        price_at_upper = latest['close'] >= latest['bb_upper']

        if price_at_lower_bb and (rsi_oversold or rsi_moderately_oversold) and above_200ma:
            confidence = 'HIGH' if (rsi_oversold and volume_spike) else 'MEDIUM'
            
            sl, tp = self.calculate_sl_tp_pips(symbol, latest['close'], is_buy=True)
            
            return {
                'signal': 'BUY',
                'strategy': 'Mean Reversion',
                'confidence': confidence,
                'entry': latest['close'],
                'stop_loss': sl,
                'take_profit': tp,
                'reason': f"Lower BB touch, RSI={latest['rsi']:.1f}, Above 200MA"
            }

        elif price_at_middle or price_at_upper:
            return {
                'signal': 'SELL',
                'strategy': 'Mean Reversion',
                'reason': f"Price at {'upper' if price_at_upper else 'middle'} BB - Take profit"
            }

        return {'signal': 'HOLD', 'reason': 'No mean reversion setup'}

    def momentum_signal(self, data: pd.DataFrame, vix: float, symbol: str) -> Dict[str, any]:
        """Momentum Signal Logic"""
        if len(data) < Config.MA_LONG or data['ma_200'].isna().iloc[-1]:
            return {'signal': 'HOLD', 'reason': 'Insufficient data for 200-day MA'}

        latest = data.iloc[-1]
        prev = data.iloc[-2]

        if pd.isna(latest['ma_fast']) or pd.isna(latest['ma_slow']):
            return {'signal': 'HOLD', 'reason': 'Moving averages not ready'}

        if vix > Config.VIX_WARNING:
            return {'signal': 'HOLD', 'reason': f'VIX too high ({vix}) for momentum'}

        golden_cross = (latest['ma_fast'] > latest['ma_slow'] and 
                       prev['ma_fast'] <= prev['ma_slow'])

        death_cross = (latest['ma_fast'] < latest['ma_slow'] and 
                      prev['ma_fast'] >= prev['ma_slow'])

        in_uptrend = latest['ma_fast'] > latest['ma_slow']

        if golden_cross or (in_uptrend and latest['close'] > latest['ma_fast']):
            sl, tp = self.calculate_sl_tp_pips(symbol, latest['close'], is_buy=True)
            
            return {
                'signal': 'BUY',
                'strategy': 'Momentum',
                'confidence': 'HIGH' if golden_cross else 'MEDIUM',
                'entry': latest['close'],
                'stop_loss': sl,
                'take_profit': tp,
                'reason': f"{'Golden Cross' if golden_cross else 'Uptrend continuation'}"
            }

        elif death_cross or (latest['close'] < latest['ma_fast'] * 0.96):
            return {
                'signal': 'SELL',
                'strategy': 'Momentum',
                'reason': f"{'Death Cross' if death_cross else 'Trend breakdown'}"
            }

        return {'signal': 'HOLD', 'reason': 'No momentum setup'}


# ============================================================================
# POSITION MANAGER (ENHANCED V3.0)
# ============================================================================

class PositionManager:
    """Manage positions, risk, and order execution"""

    def __init__(self, alert_system: AlertSystem, performance_tracker: PerformanceTracker):
        self.account_balance = 0
        self.equity = 0
        self.leverage = 1000  # Default
        self.alert_system = alert_system
        self.performance_tracker = performance_tracker
        self.trade_allowed = True

    def update_account_info(self):
        """Get current account information"""
        try:
            account_info = mt5.account_info()
            if account_info is not None:
                self.account_balance = account_info.balance
                self.equity = account_info.equity
                self.leverage = account_info.leverage  # FIX: Get actual leverage
                logger.info(f"Account Balance: ${self.account_balance:,.2f} | Equity: ${self.equity:,.2f}")
            else:
                logger.error("Failed to get account info")
        except Exception as e:
            logger.error(f"Error updating account info: {e}")

    def calculate_position_size(self, symbol: str, entry_price: float,
                               stop_loss: float, benner_allocation: float) -> float:
        """Calculate position size with proper risk management"""
        try:
            risk_amount = self.account_balance * Config.MAX_POSITION_SIZE_PCT
            risk_amount *= benner_allocation
            
            price_risk = abs(entry_price - stop_loss)
            
            if price_risk <= 0:
                logger.warning(f"Invalid price risk for {symbol}: {price_risk}")
                return 0
            
            position_value = risk_amount / (price_risk / entry_price)
            
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                if not mt5.symbol_select(symbol, True):
                    logger.error(f"Failed to select symbol: {symbol}")
                    return 0
                symbol_info = mt5.symbol_info(symbol)
            
            if symbol_info is None:
                logger.error(f"Cannot get symbol info for {symbol}")
                return 0
            
            # Get contract size
            contract_size = 100000  # Default
            
            if hasattr(symbol_info, 'trade_contract_size') and symbol_info.trade_contract_size > 0:
                contract_size = symbol_info.trade_contract_size
            elif hasattr(symbol_info, 'contract_size') and symbol_info.contract_size > 0:
                contract_size = symbol_info.contract_size
            elif symbol == 'XAUUSD':
                contract_size = 100
            else:
                logger.info(f"Using default contract size of {contract_size} for {symbol}")
            
            lots = position_value / (entry_price * contract_size)
            
            lot_step = symbol_info.volume_step if symbol_info.volume_step > 0 else 0.01  # FIX: Edge case
            min_lot = symbol_info.volume_min
            max_lot = symbol_info.volume_max
            
            if lot_step > 0:
                lots = round(lots / lot_step) * lot_step
            else:
                lots = round(lots, 2)  # FIX: Fallback rounding
            
            lots = max(min_lot, min(lots, max_lot))
            
            # FIX: Use actual leverage
            margin_required = (lots * contract_size * entry_price) / self.leverage
            
            logger.info(f"Position size for {symbol}: {lots:.3f} lots "
                       f"(Risk: ${risk_amount:.2f}, Margin: ${margin_required:.2f})")
            
            return lots
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            return 0

    def validate_order_parameters(self, symbol: str, price: float, sl: float, tp: float, order_type: int) -> bool:
        """Validate order parameters before sending"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Cannot get symbol info for {symbol}")
                return False
            
            point = symbol_info.point
            
            if order_type == mt5.ORDER_TYPE_BUY:
                if sl >= price:
                    logger.error(f"Stop loss ({sl}) must be below price ({price}) for BUY order")
                    return False
                if tp <= price:
                    logger.error(f"Take profit ({tp}) must be above price ({price}) for BUY order")
                    return False
            else:
                if sl <= price:
                    logger.error(f"Stop loss ({sl}) must be above price ({price}) for SELL order")
                    return False
                if tp >= price:
                    logger.error(f"Take profit ({tp}) must be below price ({price}) for SELL order")
                    return False
            
            sl_distance = abs(price - sl) / point
            tp_distance = abs(tp - price) / point
            
            if sl_distance < 10:
                logger.error(f"Stop loss is too close to price: {sl_distance} points")
                return False
            
            if tp_distance < 10:
                logger.error(f"Take profit is too close to price: {tp_distance} points")
                return False
            
            logger.info(f"Order validation passed: SL distance={sl_distance:.0f} pts, TP distance={tp_distance:.0f} pts")
            return True
            
        except Exception as e:
            logger.error(f"Error validating order parameters: {e}")
            return False

    def open_position(self, symbol: str, signal: Dict[str, any],
                      benner_allocation: float, strategy_type: str = 'mean_reversion') -> bool:
        """Open a new position with full v3.0 enhancements"""
        
        # DRY RUN MODE
        if Config.DRY_RUN:
            lot_size = self.calculate_position_size(symbol, signal['entry'], 
                                                    signal['stop_loss'], benner_allocation)
            logger.info(f"[DRY-RUN] Would open {signal['signal']} {symbol}: {lot_size:.3f} lots @ ${signal['entry']:.5f}")
            logger.info(f"[DRY-RUN] SL: ${signal['stop_loss']:.5f}, TP: ${signal['take_profit']:.5f}")
            logger.info(f"[DRY-RUN] Strategy: {signal['strategy']} | Reason: {signal['reason']}")
            return True  # Simulate success
        
        try:
            if not mt5.symbol_select(symbol, True):
                logger.error(f"Failed to select symbol {symbol}")
                return False
            
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"Symbol {symbol} not found")
                return False
            
            # Check for existing positions
            positions = mt5.positions_get(symbol=symbol)
            if positions and len(positions) > 0:
                logger.info(f"Already have position in {symbol}")
                return False

            lot_size = self.calculate_position_size(
                symbol,
                signal['entry'],
                signal['stop_loss'],
                benner_allocation
            )

            if lot_size <= 0:
                logger.warning(f"Invalid lot size for {symbol}: {lot_size}")
                return False

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"Cannot get tick data for {symbol}")
                return False
            
            if signal['signal'] == 'BUY':
                price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY
            elif signal['signal'] == 'SELL':
                price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            else:
                logger.error(f"Invalid signal direction: {signal['signal']}")
                return False
            
            sl = signal['stop_loss']
            tp = signal['take_profit']
            
            if not self.validate_order_parameters(symbol, price, sl, tp, order_type):
                logger.error(f"Order parameters validation failed for {symbol}")
                return False
            
            # Select magic number based on strategy
            magic_numbers = {
                'mean_reversion': Config.MAGIC_MEAN_REVERSION,
                'momentum': Config.MAGIC_MOMENTUM,
                'defensive': Config.MAGIC_DEFENSIVE
            }
            magic = magic_numbers.get(strategy_type, Config.MAGIC_MEAN_REVERSION)
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": Config.SLIPPAGE,
                "magic": magic,
                "comment": f"{signal['strategy']} - {signal['reason'][:30]}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            logger.info(f"Attempting to open position: {symbol}, {lot_size:.3f} lots @ ${price:.5f}")
            logger.info(f"SL: ${sl:.5f}, TP: ${tp:.5f}")
            
            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"Order send returned None for {symbol}. Check MT5 connection.")
                last_error = mt5.last_error()
                logger.error(f"MT5 Last Error: {last_error}")
                return False
            
            logger.info(f"Order result: retcode={result.retcode}, order={result.order}, "
                       f"volume={result.volume}, price={result.price}")
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order failed for {symbol}: retcode={result.retcode}, comment={result.comment}")
                last_error = mt5.last_error()
                if last_error:
                    logger.error(f"MT5 Error Details: {last_error}")
                return False

            logger.info(f"[SUCCESS] {signal['signal']} {symbol}: {lot_size:.3f} lots @ ${price:.5f}")
            logger.info(f"  Strategy: {signal['strategy']} | Reason: {signal['reason']}")
            logger.info(f"  SL: ${sl:.5f} | TP: ${tp:.5f}")
            
            # Send alert
            self.alert_system.send_trade_alert(
                signal['signal'], symbol, lot_size, price, sl, tp, signal['strategy']
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error opening position for {symbol}: {e}", exc_info=True)
            return False

    def close_position(self, symbol: str, reason: str = "Signal") -> bool:
        """Close existing position"""
        
        # DRY RUN MODE
        if Config.DRY_RUN:
            logger.info(f"[DRY-RUN] Would close position in {symbol} | Reason: {reason}")
            return True
        
        try:
            positions = mt5.positions_get(symbol=symbol)
            if not positions or len(positions) == 0:
                logger.info(f"No positions to close for {symbol}")
                return False

            position = positions[0]
            
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"Cannot get tick data for {symbol}")
                return False
            
            if position.type == mt5.ORDER_TYPE_BUY:
                price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            else:
                price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": position.volume,
                "type": order_type,
                "position": position.ticket,
                "price": price,
                "deviation": Config.SLIPPAGE,
                "magic": position.magic,
                "comment": f"Close: {reason}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"Close order returned None for {symbol}")
                return False

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Close failed for {symbol}: {result.comment}")
                return False

            profit = position.profit
            logger.info(f"[CLOSE] {symbol}: {position.volume} lots | P/L: ${profit:.2f} | Reason: {reason}")
            
            # Record trade in performance tracker
            self.performance_tracker.record_trade(
                symbol=symbol,
                action='CLOSE',
                lots=position.volume,
                entry=position.price_open,
                exit_price=price,
                profit=profit,
                strategy=position.comment.split(' - ')[0] if ' - ' in position.comment else 'Unknown',
                reason=reason
            )
            
            # Send alert
            self.alert_system.send_close_alert(symbol, position.volume, profit, reason)
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return False

    def update_trailing_stops(self):
        """Update trailing stops for winning positions"""
        try:
            positions = mt5.positions_get()
            if not positions:
                return
            
            for position in positions:
                # Only trail winning positions
                if position.profit <= 0:
                    continue
                
                symbol = position.symbol
                symbol_info = mt5.symbol_info(symbol)
                if not symbol_info:
                    continue
                
                tick = mt5.symbol_info_tick(symbol)
                if not tick:
                    continue
                
                # Calculate pip value
                point = symbol_info.point
                pip_value = point * 10
                if 'JPY' in symbol:
                    pip_value = point * 100
                if symbol == 'XAUUSD':
                    pip_value = 0.01
                
                trail_distance = Config.TRAILING_STOP_PIPS * pip_value
                
                if position.type == mt5.ORDER_TYPE_BUY:
                    new_sl = tick.bid - trail_distance
                    
                    # Only move SL up, never down
                    if new_sl > position.sl:
                        request = {
                            "action": mt5.TRADE_ACTION_SLTP,
                            "symbol": symbol,
                            "position": position.ticket,
                            "sl": new_sl,
                            "tp": position.tp
                        }
                        
                        result = mt5.order_send(request)
                        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                            logger.info(f"[TRAIL] Updated {symbol} SL from {position.sl:.5f} to {new_sl:.5f}")
                
                else:  # SELL position
                    new_sl = tick.ask + trail_distance
                    
                    # Only move SL down, never up
                    if new_sl < position.sl or position.sl == 0:
                        request = {
                            "action": mt5.TRADE_ACTION_SLTP,
                            "symbol": symbol,
                            "position": position.ticket,
                            "sl": new_sl,
                            "tp": position.tp
                        }
                        
                        result = mt5.order_send(request)
                        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                            logger.info(f"[TRAIL] Updated {symbol} SL from {position.sl:.5f} to {new_sl:.5f}")
                            
        except Exception as e:
            logger.error(f"Error updating trailing stops: {e}")

    def get_portfolio_exposure(self) -> float:
        """Calculate current portfolio exposure"""
        try:
            positions = mt5.positions_get()
            if not positions:
                return 0.0

            total_value = 0
            for pos in positions:
                symbol_info = mt5.symbol_info(pos.symbol)
                if symbol_info:
                    contract_size = 100000
                    if hasattr(symbol_info, 'trade_contract_size') and symbol_info.trade_contract_size > 0:
                        contract_size = symbol_info.trade_contract_size
                    elif hasattr(symbol_info, 'contract_size') and symbol_info.contract_size > 0:
                        contract_size = symbol_info.contract_size
                    
                    position_value = pos.volume * contract_size * pos.price_open
                    total_value += position_value
            
            return total_value / self.equity if self.equity > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating portfolio exposure: {e}")
            return 0.0

# CONTINUATION OF BENNER BOT V3.0
# This is Part 3 

# ============================================================================
# MAIN TRADING BOT V3.0
# ============================================================================

class BennerTradingBot:
    """Main trading bot orchestrating the hybrid strategy - v3.0"""

    def __init__(self):
        self.regime_detector = MarketRegime()
        self.signal_generator = SignalGenerator()
        self.indicators = TechnicalIndicators()
        self.market_data = None
        self.alert_system = AlertSystem()
        self.performance_tracker = PerformanceTracker()
        self.position_manager = PositionManager(self.alert_system, self.performance_tracker)
        self.risk_manager = RiskManager()
        self.running = False
        self.trade_allowed = True

    def initialize(self) -> bool:
        """Initialize MT5 connection"""
        logger.info("=" * 80)
        logger.info("Benner-Adjusted Hybrid Trading Bot v3.0 - ENTERPRISE EDITION")
        logger.info("=" * 80)
        
        # Validate configuration
        errors = Config.validate()
        if errors:
            logger.error("Configuration errors:")
            for error in errors:
                logger.error(f"  - {error}")
            logger.error("\nPlease set environment variables in .env file")
            return False
        
        logger.info(f"DRY RUN MODE: {Config.DRY_RUN}")
        if Config.DRY_RUN:
            logger.warning("⚠️  DRY RUN MODE ENABLED - No real trades will be executed!")
        
        # Initialize MT5
        if not mt5.initialize():
            logger.error("MT5 initialization failed")
            logger.error("Please ensure MetaTrader 5 is running")
            return False

        logger.info(f"MT5 Version: {mt5.version()}")

        # Login
        authorized = mt5.login(
            Config.MT5_LOGIN,
            password=Config.MT5_PASSWORD,
            server=Config.MT5_SERVER
        )

        if not authorized:
            logger.error("MT5 login failed")
            logger.error(f"Login: {Config.MT5_LOGIN}, Server: {Config.MT5_SERVER}")
            mt5.shutdown()
            return False

        logger.info(f"[SUCCESS] Connected to MT5 account: {Config.MT5_LOGIN}")

        # Verify connection
        if not self.verify_mt5_connection():
            logger.error("MT5 connection verification failed")
            mt5.shutdown()
            return False

        # Check symbols
        if not self.check_symbols_availability():
            logger.warning("Some symbols are unavailable. Trading may be limited.")

        # Initialize market data provider
        self.market_data = MarketDataProvider()

        # Update account info
        self.position_manager.update_account_info()
        
        # Send startup alert
        self.alert_system.send(
            f"Bot v3.0 started successfully\n"
            f"Account: {Config.MT5_LOGIN}\n"
            f"Balance: ${self.position_manager.account_balance:,.2f}\n"
            f"DRY RUN: {Config.DRY_RUN}",
            'SUCCESS'
        )

        return True

    def verify_mt5_connection(self):
        """Verify MT5 connection is working"""
        logger.info("\n[MT5 CONNECTION VERIFICATION]")
        logger.info("-" * 60)
        
        terminal_info = mt5.terminal_info()
        if terminal_info:
            logger.info(f"Terminal: {terminal_info.name}")
            logger.info(f"Company: {terminal_info.company}")
            logger.info(f"Connected: {terminal_info.connected}")
            logger.info(f"Trade Allowed: {terminal_info.trade_allowed}")
            
            if not terminal_info.trade_allowed:
                logger.warning("\n⚠️  AUTOMATED TRADING IS DISABLED IN MT5!")
                logger.warning("To enable automated trading:")
                logger.warning("1. Go to Tools -> Options -> Expert Advisors")
                logger.warning("2. Check 'Allow automated trading'")
                logger.warning("3. Click OK and restart MT5")
                self.trade_allowed = False
            else:
                self.trade_allowed = True
                logger.info("✓ Automated trading is enabled in MT5")
        else:
            logger.error("Cannot get terminal info")
            return False
        
        account_info = mt5.account_info()
        if account_info:
            logger.info(f"Account: {account_info.login}")
            logger.info(f"Balance: ${account_info.balance:.2f}")
            logger.info(f"Equity: ${account_info.equity:.2f}")
            logger.info(f"Leverage: 1:{account_info.leverage}")
        else:
            logger.error("Cannot get account info")
            return False
        
        return True

    def check_symbols_availability(self):
        """Check if all symbols are available for trading"""
        logger.info("\n[SYMBOL AVAILABILITY CHECK]")
        logger.info("-" * 60)
        
        all_symbols = set()
        for strategy_symbols in Config.SYMBOLS.values():
            all_symbols.update(strategy_symbols)
        
        available = []
        unavailable = []
        
        for symbol in all_symbols:
            if mt5.symbol_select(symbol, True):
                info = mt5.symbol_info(symbol)
                if info:
                    available.append(symbol)
                    logger.info(f"✓ {symbol}: Available (Min: {info.volume_min}, Max: {info.volume_max})")
                else:
                    unavailable.append(symbol)
                    logger.error(f"✗ {symbol}: Info not available")
            else:
                unavailable.append(symbol)
                logger.error(f"✗ {symbol}: Not found")
        
        if unavailable:
            logger.warning(f"\n{len(unavailable)} symbols unavailable: {unavailable}")
        
        logger.info(f"\nTotal: {len(all_symbols)} | Available: {len(available)} | Unavailable: {len(unavailable)}")
        
        return len(unavailable) == 0

    def get_market_data(self, symbol: str, timeframe: int = mt5.TIMEFRAME_H4,
                        bars: int = 300) -> pd.DataFrame:
        """Fetch historical data and calculate indicators"""
        try:
            mt5.symbol_select(symbol, True)
            
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)

            if rates is None or len(rates) == 0:
                logger.warning(f"No data for {symbol} - trying alternative method")
                rates = mt5.copy_rates_from(symbol, timeframe, 
                                           datetime.now(timezone.utc) - timedelta(days=30), bars)

            if rates is None or len(rates) < Config.MIN_BARS_REQUIRED:
                logger.warning(
                    f"Insufficient data for {symbol}: got {len(rates) if rates is not None else 0} bars")
                return pd.DataFrame()

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')

            df = self.indicators.bollinger_bands(df, Config.BB_PERIOD, Config.BB_STD)
            df = self.indicators.rsi(df, Config.RSI_PERIOD)
            df = self.indicators.moving_averages(df, Config.MA_FAST, Config.MA_SLOW, Config.MA_LONG)
            df = self.indicators.volume_analysis(df)

            latest = df.iloc[-1]
            bb_percent = ((latest['close'] - latest['bb_lower']) / 
                         (latest['bb_upper'] - latest['bb_lower']) * 100) if (
                         latest['bb_upper'] - latest['bb_lower']) > 0 else 0
            
            logger.info(f"{symbol}: {len(df)} bars, Price: ${latest['close']:.2f}, "
                       f"RSI: {latest['rsi']:.1f}, BB%: {bb_percent:.1f}%")

            return df
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return pd.DataFrame()

    def get_benner_allocation(self) -> Dict[str, any]:
        """Get current month's Benner cycle allocation"""
        current_month = datetime.now().strftime('%b-%Y')

        if current_month in Config.BENNER_CALENDAR:
            return Config.BENNER_CALENDAR[current_month]
        else:
            return {'allocation': 0.40, 'phase': 'Conservative'}

    def process_mean_reversion_symbols(self, vix: float, benner: Dict[str, any]):
        """Process mean reversion strategy symbols"""
        logger.info("\n[MEAN REVERSION ANALYSIS] 60% allocation")
        logger.info("-" * 60)

        for symbol in Config.SYMBOLS['mean_reversion']:
            try:
                data = self.get_market_data(symbol)
                if data.empty:
                    continue

                signal = self.signal_generator.mean_reversion_signal(data, symbol)

                latest = data.iloc[-1]
                logger.info(f"\n{symbol}: ${latest['close']:.2f} | RSI: {latest['rsi']:.1f}")
                logger.info(f"Signal: {signal['signal']} | {signal['reason']}")

                if signal['signal'] == 'BUY':
                    logger.info(f"BUY Opportunity: {signal['reason']}")
                    
                    # Apply filters
                    if latest['rsi'] < Config.RSI_BUY_THRESHOLD:
                        # Check risk management
                        current_exposure = self.position_manager.get_portfolio_exposure()
                        can_trade, risk_msg = self.risk_manager.can_open_position(symbol, current_exposure)
                        
                        if can_trade and self.trade_allowed:
                            self.position_manager.open_position(
                                symbol, signal, benner['allocation'] * 0.60, 'mean_reversion'
                            )
                        else:
                            logger.warning(f"Cannot open {symbol}: {risk_msg}")
                    else:
                        logger.info(f"Skipping BUY - RSI ({latest['rsi']:.1f}) above threshold")
                        
                elif signal['signal'] == 'SELL':
                    self.position_manager.close_position(symbol, signal['reason'])
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue

    def process_momentum_symbols(self, vix: float, benner: Dict[str, any]):
        """Process momentum strategy symbols"""
        logger.info("\n[MOMENTUM ANALYSIS] 30% allocation")
        logger.info("-" * 60)

        for symbol in Config.SYMBOLS['momentum']:
            try:
                data = self.get_market_data(symbol)
                if data.empty:
                    continue

                signal = self.signal_generator.momentum_signal(data, vix, symbol)

                latest = data.iloc[-1]
                ma_fast = latest.get('ma_fast', 0)
                ma_slow = latest.get('ma_slow', 0)
                logger.info(f"\n{symbol}: ${latest['close']:.2f} | MA Fast: {ma_fast:.2f} | MA Slow: {ma_slow:.2f}")
                logger.info(f"Signal: {signal['signal']} | {signal['reason']}")

                if signal['signal'] == 'BUY':
                    logger.info(f"Momentum BUY: {signal['reason']}")
                    
                    if latest['close'] > latest.get('ma_200', 0):
                        current_exposure = self.position_manager.get_portfolio_exposure()
                        can_trade, risk_msg = self.risk_manager.can_open_position(symbol, current_exposure)
                        
                        if can_trade and self.trade_allowed:
                            self.position_manager.open_position(
                                symbol, signal, benner['allocation'] * 0.30, 'momentum'
                            )
                        else:
                            logger.warning(f"Cannot open {symbol}: {risk_msg}")
                    else:
                        logger.info("Skipping BUY - Price below 200MA")
                        
                elif signal['signal'] == 'SELL':
                    self.position_manager.close_position(symbol, signal['reason'])
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue

    def run_cycle(self):
        """Execute one complete trading cycle"""
        try:
            logger.info("\n" + "=" * 80)
            logger.info(f"TRADING CYCLE - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            logger.info("=" * 80)
            
            # Check weekend
            if MarketHours.is_weekend():
                next_open = MarketHours.next_open_time()
                logger.info(f"[WEEKEND] Market closed. Next open: {next_open.strftime('%Y-%m-%d %H:%M UTC')}")
                return

            # Check MT5 connection
            if not mt5.terminal_info():
                logger.error("MT5 connection lost. Attempting to reconnect...")
                mt5.shutdown()
                time.sleep(2)
                if not self.initialize():
                    logger.error("Failed to reconnect. Skipping cycle.")
                    return

            # Update account info
            self.position_manager.update_account_info()

            # Get market indicators
            market_indicators = self.market_data.get_market_indicators()
            vix = market_indicators['vix']
            spx = market_indicators['spx']

            # Detect market regime
            regime = self.regime_detector.detect_regime(vix, spx)
            warnings = self.regime_detector.get_warnings()

            logger.info(f"\n[MARKET REGIME] {regime['regime']}")
            logger.info(f"Action: {regime['action']} | Message: {regime['message']}")
            logger.info(f"VIX: {vix:.2f} | SPX: {spx:.2f}")

            if warnings:
                logger.warning("\n[MARKET WARNINGS]")
                for warning in warnings:
                    logger.warning(f"[{warning['level']}] {warning['message']}")
                
                # Send critical warnings via Telegram
                if any(w['level'] == 'CRITICAL' for w in warnings):
                    self.alert_system.send(
                        f"CRITICAL MARKET WARNING\n" + 
                        "\n".join([w['message'] for w in warnings if w['level'] == 'CRITICAL']),
                        'WARNING'
                    )

            # Get Benner allocation
            benner = self.get_benner_allocation()
            logger.info(f"\n[BENNER CYCLE] {benner['phase']} | Allocation: {benner['allocation'] * 100:.0f}%")

            # Emergency exit if needed
            if regime['action'] == 'EXIT':
                logger.critical("[EMERGENCY EXIT MODE] Closing all positions")
                self.alert_system.send("EMERGENCY EXIT MODE ACTIVATED", 'ERROR')
                
                positions = mt5.positions_get()
                if positions:
                    for pos in positions:
                        self.position_manager.close_position(pos.symbol, "Emergency Exit")
                return

            # Process strategies
            self.process_mean_reversion_symbols(vix, benner)

            if vix < Config.VIX_WARNING:
                self.process_momentum_symbols(vix, benner)
            else:
                logger.info("\n[MOMENTUM ANALYSIS] SKIPPED (VIX too high)")

            # Update trailing stops
            self.position_manager.update_trailing_stops()

            # Portfolio summary
            exposure = self.position_manager.get_portfolio_exposure()
            positions = mt5.positions_get()
            
            logger.info(f"\n[PORTFOLIO SUMMARY]")
            logger.info(f"Exposure: {exposure * 100:.1f}% (Target: {benner['allocation'] * 100:.0f}%)")
            logger.info(f"Open Positions: {len(positions) if positions else 0}")
            
            if positions:
                total_profit = sum(p.profit for p in positions)
                logger.info(f"Total Unrealized P/L: ${total_profit:.2f}")
                for pos in positions:
                    logger.info(f"  {pos.symbol}: {pos.volume:.3f} lots @ ${pos.price_open:.5f} | "
                               f"P/L: ${pos.profit:.2f}")
            else:
                logger.info("No open positions")
            
            # Performance stats
            stats = self.performance_tracker.get_statistics()
            if stats['total_trades'] > 0:
                logger.info(f"\n[PERFORMANCE] Trades: {stats['total_trades']}, "
                           f"Win Rate: {stats['win_rate']:.1f}%, "
                           f"Total P/L: ${stats['total_profit']:.2f}")

            logger.info("\n" + "=" * 80)
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
            self.alert_system.send(f"Trading cycle error: {str(e)}", 'ERROR')

    def run(self):
        """Main loop"""
        self.running = True

        logger.info(f"\n[BOT STARTED] Update interval: {Config.UPDATE_INTERVAL}s")
        logger.info(f"Symbols tracked: {sum(len(v) for v in Config.SYMBOLS.values())}")

        try:
            while self.running:
                self.run_cycle()

                logger.info(f"\n[WAITING] {Config.UPDATE_INTERVAL}s until next cycle...")
                for i in range(Config.UPDATE_INTERVAL):
                    time.sleep(1)
                    if not self.running:
                        break

        except KeyboardInterrupt:
            logger.info("\n\n[STOPPED] Bot stopped by user")
        except Exception as e:
            logger.error(f"\n\n[FATAL ERROR] {e}", exc_info=True)
            self.alert_system.send(f"Bot crashed: {str(e)}", 'ERROR')
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        try:
            logger.info("\n" + "=" * 80)
            logger.info("SHUTTING DOWN")
            logger.info("=" * 80)

            # Final account update
            self.position_manager.update_account_info()

            # List open positions
            positions = mt5.positions_get()
            if positions:
                total_profit = sum(p.profit for p in positions)
                logger.info(f"\nOpen positions: {len(positions)}")
                logger.info(f"Total unrealized P/L: ${total_profit:.2f}")
                logger.info("Note: Positions will remain open after shutdown")
            else:
                logger.info("\nNo open positions")

            # Final performance stats
            self.performance_tracker._log_statistics()

            # Shutdown MT5
            mt5.shutdown()
            logger.info("\n[SUCCESS] MT5 connection closed")
            logger.info("Bot terminated successfully\n")
            
            # Send shutdown alert
            self.alert_system.send("Bot shutdown successfully", 'INFO')
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    try:
        print("\n" + "="*80)
        print("BENNER TRADING BOT v3.0 - ENTERPRISE EDITION")
        print("="*80 + "\n")
        
        # Check for .env file
        if not DOTENV_AVAILABLE:
            print("WARNING: python-dotenv not installed")
            print("Install with: pip install python-dotenv")
            print("")
        
        if not os.path.exists('.env'):
            print("ERROR: .env file not found!")
            print("Please create a .env file with your MT5 credentials")
            print("See .env.template for an example")
            print("")
            return
        
        logger.info("Starting Benner Trading Bot v3.0...")
        
        bot = BennerTradingBot()

        if not bot.initialize():
            logger.error("Failed to initialize bot")
            return

        bot.run()
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)


if __name__ == "__main__":
    main()