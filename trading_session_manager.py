# ═══════════════════════════════════════════════════════════════════════════
# TRADING SESSION MANAGER - BENNER BOT v4.1
# Market Hours Detection, Session-based Trading, and Liquidity Checks
# ═══════════════════════════════════════════════════════════════════════════

import logging
from datetime import datetime, time, timedelta
from typing import Dict, Tuple, Optional, List
import MetaTrader5 as mt5
from pytz import timezone, UTC

logger = logging.getLogger(__name__)


class TradingSessionManager:
    """
    Manages trading sessions and market hours including:
    - Predefined session times (Asian, European, American)
    - Automatic market hours detection via MT5 API
    - Liquidity monitoring (bid-ask spread)
    - Weekend/holiday handling for 24/7 instruments
    """

    def __init__(self, config: Dict):
        """
        Initialize trading session manager.
        
        Args:
            config: Configuration dictionary from config_loader
        """
        self.config = config
        
        # Session settings
        self.enable_trading_sessions = config.get('ENABLE_TRADING_SESSIONS', True)
        self.enable_auto_market_hours = config.get('ENABLE_AUTO_MARKET_HOURS_DETECTION', True)
        self.market_hours_check_interval = config.get('MARKET_HOURS_CHECK_INTERVAL', 60)  # minutes
        self.liquidity_spread_threshold = config.get('LIQUIDITY_MIN_SPREAD_THRESHOLD', 2)  # pips
        
        # Crypto settings
        self.crypto_trade_weekends = config.get('CRYPTO_TRADE_WEEKENDS', True)
        
        # Parse session times from config
        self.sessions = self._parse_sessions(config)
        
        # Market hours cache (to avoid excessive API calls)
        self.market_hours_cache = {}
        self.last_market_check = {}
        
        # UTC timezone for consistency
        self.utc_tz = UTC
        
        logger.info("TradingSessionManager initialized")
        logger.info(f"  Trading sessions enabled: {self.enable_trading_sessions}")
        logger.info(f"  Auto market hours detection: {self.enable_auto_market_hours}")
        logger.info(f"  Crypto weekend trading: {self.crypto_trade_weekends}")

    def _parse_sessions(self, config: Dict) -> Dict[str, Dict]:
        """
        Parse session times from configuration.
        
        Returns:
            Dictionary of sessions with start/end times
        """
        sessions = {}
        
        # FOREX sessions
        forex_sessions = {
            'ASIA': ('FOREX_ASIA_SESSION_START', 'FOREX_ASIA_SESSION_END'),
            'EUROPE': ('FOREX_EUROPE_SESSION_START', 'FOREX_EUROPE_SESSION_END'),
            'AMERICA': ('FOREX_AMERICA_SESSION_START', 'FOREX_AMERICA_SESSION_END'),
        }
        
        for session_name, (start_key, end_key) in forex_sessions.items():
            start_str = config.get(start_key)
            end_str = config.get(end_key)
            
            if start_str and end_str:
                try:
                    start_time = self._parse_time(start_str)
                    end_time = self._parse_time(end_str)
                    sessions[f'FOREX_{session_name}'] = {
                        'start': start_time,
                        'end': end_time,
                        'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'NZDUSD', 'USDCHF'],
                        'category': 'FOREX'
                    }
                except ValueError as e:
                    logger.error(f"Failed to parse {session_name} session times: {e}")
        
        # COMMODITY sessions
        commodity_sessions = {
            'GOLD': ('COMMODITY_GOLD_SESSION_START', 'COMMODITY_GOLD_SESSION_END'),
            'SILVER': ('COMMODITY_SILVER_SESSION_START', 'COMMODITY_SILVER_SESSION_END'),
        }
        
        for session_name, (start_key, end_key) in commodity_sessions.items():
            start_str = config.get(start_key)
            end_str = config.get(end_key)
            
            if start_str and end_str:
                try:
                    start_time = self._parse_time(start_str)
                    end_time = self._parse_time(end_str)
                    symbol = f'{session_name}USD' if session_name != 'GOLD' else 'XAUUSD'
                    sessions[f'COMMODITY_{session_name}'] = {
                        'start': start_time,
                        'end': end_time,
                        'symbols': [symbol],
                        'category': 'COMMODITY'
                    }
                except ValueError as e:
                    logger.error(f"Failed to parse {session_name} session times: {e}")
        
        # CRYPTO sessions (24/7 but weekend handling available)
        crypto_start_str = config.get('CRYPTO_SESSION_START')
        crypto_end_str = config.get('CRYPTO_SESSION_END')
        if crypto_start_str and crypto_end_str:
            try:
                crypto_start = self._parse_time(crypto_start_str)
                crypto_end = self._parse_time(crypto_end_str)
                sessions['CRYPTO_24_7'] = {
                    'start': crypto_start,
                    'end': crypto_end,
                    'symbols': ['BTCUSD', 'ETHUSD', 'LTCUSD'],
                    'category': 'CRYPTO'
                }
            except ValueError as e:
                logger.error(f"Failed to parse crypto session times: {e}")
        
        logger.info(f"Parsed {len(sessions)} trading sessions")
        for session_name, details in sessions.items():
            logger.debug(f"  {session_name}: {details['start']} - {details['end']} "
                        f"(symbols: {', '.join(details['symbols'])})")
        
        return sessions

    @staticmethod
    def _parse_time(time_str: str) -> time:
        """
        Parse time string in HH:MM format.
        
        Args:
            time_str: Time string in HH:MM format
            
        Returns:
            time object
            
        Raises:
            ValueError: If time format is invalid
        """
        try:
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError(f"Invalid time values: {time_str}")
            return time(hour, minute)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Cannot parse time '{time_str}': {e}")

    def is_in_trading_session(self, symbol: str) -> Tuple[bool, str]:
        """
        Check if symbol is in an active trading session.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD', 'XAUUSD', 'BTCUSD')
            
        Returns:
            Tuple of (is_trading: bool, session_name: str)
        """
        if not self.enable_trading_sessions:
            return True, "Trading sessions disabled"
        
        # Get current UTC time
        current_utc = datetime.now(self.utc_tz).time()
        current_date = datetime.now(self.utc_tz).date()
        current_weekday = datetime.now(self.utc_tz).weekday()  # 0=Monday, 6=Sunday
        
        # Check each session
        for session_name, session_info in self.sessions.items():
            if symbol not in session_info['symbols']:
                continue
            
            start = session_info['start']
            end = session_info['end']
            
            # Handle sessions that cross midnight (e.g., 22:00 - 08:00)
            if start > end:  # Overnight session
                in_session = current_utc >= start or current_utc < end
            else:  # Normal session
                in_session = start <= current_utc < end
            
            if in_session:
                # Special handling for weekends
                if 'CRYPTO' in session_name and current_weekday >= 5:  # Saturday or Sunday
                    if not self.crypto_trade_weekends:
                        return False, f"{session_name} (Weekend - crypto trading disabled)"
                
                return True, session_name
        
        return False, "No active session"

    def check_market_hours_via_api(self, symbol: str) -> Tuple[bool, str]:
        """
        Use MetaTrader 5 API to check if symbol is trading.
        
        This is more reliable than manual session times as it:
        - Checks actual broker market hours
        - Accounts for holidays
        - Detects emergency closures
        - Monitors bid-ask spread for liquidity
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Tuple of (is_trading: bool, reason: str)
        """
        if not self.enable_auto_market_hours:
            return True, "API market hours check disabled"
        
        try:
            # Check cache first (avoid excessive API calls)
            cache_key = f"{symbol}_{datetime.now().strftime('%H:%M')}"
            if cache_key in self.market_hours_cache:
                cached_result, cached_reason = self.market_hours_cache[cache_key]
                return cached_result, cached_reason
            
            # Get symbol info from MT5
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return False, f"Symbol not found: {symbol}"
            
            # Check if symbol is visible (available for trading)
            if not symbol_info.visible:
                return False, "Symbol not visible"
            
            # Check bid-ask spread as liquidity indicator
            current_tick = mt5.symbol_info_tick(symbol)
            if current_tick is None:
                return False, "Cannot get current tick"
            
            bid = current_tick.bid
            ask = current_tick.ask
            
            # Get point value (for pip calculation)
            point = symbol_info.point
            if point == 0:
                return False, "Invalid point value"
            
            # Calculate spread in pips
            spread_pips = (ask - bid) / point
            
            # If spread is too wide, market likely closed or low liquidity
            if spread_pips > self.liquidity_spread_threshold:
                reason = f"Low liquidity (spread: {spread_pips:.1f} pips, threshold: {self.liquidity_spread_threshold})"
                result = False
            else:
                reason = f"Active trading (spread: {spread_pips:.1f} pips)"
                result = True
            
            # Cache result for this minute
            self.market_hours_cache[cache_key] = (result, reason)
            
            return result, reason
            
        except Exception as e:
            logger.error(f"Error checking market hours for {symbol}: {e}")
            return False, f"API error: {str(e)}"

    def can_trade_symbol(self, symbol: str) -> Tuple[bool, str]:
        """
        Determine if trading is allowed for a symbol using all checks.
        
        Uses both predefined sessions and API market hours checks.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Tuple of (can_trade: bool, reason: str)
        """
        # First, check predefined sessions
        if self.enable_trading_sessions:
            in_session, session_name = self.is_in_trading_session(symbol)
            if not in_session:
                return False, f"Outside trading session ({session_name})"
        
        # Then, check API market hours (more authoritative)
        if self.enable_auto_market_hours:
            api_trading, api_reason = self.check_market_hours_via_api(symbol)
            if not api_trading:
                return False, f"API check failed: {api_reason}"
        
        return True, "OK - Can trade"

    def get_session_summary(self) -> Dict:
        """
        Get summary of all configured sessions.
        
        Returns:
            Dictionary with session information
        """
        summary = {
            'trading_sessions_enabled': self.enable_trading_sessions,
            'auto_market_hours_enabled': self.enable_auto_market_hours,
            'crypto_weekend_trading': self.crypto_trade_weekends,
            'sessions': {}
        }
        
        for session_name, session_info in self.sessions.items():
            summary['sessions'][session_name] = {
                'start': str(session_info['start']),
                'end': str(session_info['end']),
                'symbols': session_info['symbols'],
                'category': session_info['category']
            }
        
        return summary

    def get_weekend_tradeable_symbols(self) -> List[str]:
        """
        Get list of symbols that can be traded on weekends.
        
        Returns:
            List of symbols that are active 24/7
        """
        weekend_symbols = []
        
        for session_name, session_info in self.sessions.items():
            if 'CRYPTO' in session_name or 'COMMODITY' in session_name:
                # These are typically 24/5 or 24/7
                if self.crypto_trade_weekends or 'COMMODITY' in session_name:
                    weekend_symbols.extend(session_info['symbols'])
        
        return list(set(weekend_symbols))

    def clear_market_hours_cache(self) -> None:
        """Clear the market hours cache to force API refresh."""
        self.market_hours_cache = {}
        logger.info("Market hours cache cleared")

    def get_next_session_for_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Get next trading session for a symbol.
        
        Useful for scheduling trades when market opens.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with next session info or None
        """
        current_time = datetime.now(self.utc_tz).time()
        
        # Find sessions for this symbol
        relevant_sessions = [
            (name, info) for name, info in self.sessions.items()
            if symbol in info['symbols']
        ]
        
        if not relevant_sessions:
            return None
        
        # Sort by start time
        relevant_sessions.sort(key=lambda x: x[1]['start'])
        
        # Find next session
        for session_name, session_info in relevant_sessions:
            if session_info['start'] > current_time:
                return {
                    'session_name': session_name,
                    'start': str(session_info['start']),
                    'end': str(session_info['end']),
                    'symbol': symbol
                }
        
        # If no session found today, return first session tomorrow
        if relevant_sessions:
            next_session_name, next_session_info = relevant_sessions[0]
            return {
                'session_name': next_session_name,
                'start': str(next_session_info['start']),
                'end': str(next_session_info['end']),
                'symbol': symbol,
                'tomorrow': True
            }
        
        return None

    def get_active_tradeable_symbols(self, all_symbols: List[str]) -> List[str]:
        """
        Get subset of symbols that are currently tradeable based on sessions.
        
        Args:
            all_symbols: List of all configured symbols
            
        Returns:
            List of symbols currently in trading sessions
        """
        tradeable = []
        
        for symbol in all_symbols:
            can_trade, _ = self.can_trade_symbol(symbol)
            if can_trade:
                tradeable.append(symbol)
        
        return tradeable
