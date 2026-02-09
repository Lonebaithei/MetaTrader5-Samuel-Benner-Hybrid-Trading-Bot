# ═══════════════════════════════════════════════════════════════════════════
# RISK MANAGEMENT MODULE - BENNER BOT v4.1
# Drawdown Tracking, Kill Switch, and Position Limits
# ═══════════════════════════════════════════════════════════════════════════

import logging
from datetime import datetime, time
from typing import Dict, Tuple, Optional, List
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Manages account-level risk controls including:
    - Daily and intraday drawdown tracking
    - Kill switch activation when limits breached
    - Position count enforcement
    - Equity monitoring and alerts
    """

    def __init__(self, config: Dict):
        """
        Initialize risk manager with configuration.
        
        Args:
            config: Configuration dictionary from config_loader
        """
        self.config = config
        
        # Drawdown settings
        self.max_daily_drawdown = config.get('MAX_DAILY_DRAWDOWN_PERCENT', 30) / 100
        self.max_intraday_drawdown = config.get('MAX_INTRADAY_DRAWDOWN_PERCENT', 20) / 100
        self.kill_switch_mode = config.get('KILL_SWITCH_MODE', 'STOP_OPENING')
        self.drawdown_reset_time_str = config.get('DRAWDOWN_RESET_TIME', '00:00')
        
        # Position limits
        self.max_concurrent_positions = config.get('MAX_CONCURRENT_POSITIONS', 5)
        self.max_positions_per_symbol = config.get('MAX_POSITIONS_PER_SYMBOL', 2)
        
        # Tracking variables
        self.session_start_equity = None
        self.session_peak_equity = None
        self.daily_start_equity = None
        self.kill_switch_active = False
        self.last_reset_time = None
        
        # Alert settings
        self.enable_drawdown_alerts = config.get('ENABLE_DRAWDOWN_ALERTS', True)
        self.drawdown_alert_thresholds = [75, 50, 25]  # % of limit before triggering alert
        self.alerts_triggered = {}
        
        logger.info("RiskManager initialized with:")
        logger.info(f"  Max Daily Drawdown: {self.max_daily_drawdown*100}%")
        logger.info(f"  Max Intraday Drawdown: {self.max_intraday_drawdown*100}%")
        logger.info(f"  Kill Switch Mode: {self.kill_switch_mode}")
        logger.info(f"  Max Concurrent Positions: {self.max_concurrent_positions}")

    def initialize_session(self, account_balance: float) -> None:
        """
        Initialize tracking at session start.
        
        Args:
            account_balance: Starting account balance
        """
        self.session_start_equity = account_balance
        self.session_peak_equity = account_balance
        self.daily_start_equity = account_balance
        self.last_reset_time = datetime.now()
        self.kill_switch_active = False
        
        logger.info(f"Session initialized - Starting equity: ${account_balance:,.2f}")

    def should_reset_daily_drawdown(self) -> bool:
        """
        Check if daily drawdown counter should reset based on DRAWDOWN_RESET_TIME.
        
        Returns:
            True if reset time has been reached, False otherwise
        """
        try:
            reset_hour, reset_minute = map(int, self.drawdown_reset_time_str.split(':'))
            reset_time = time(reset_hour, reset_minute)
            current_time = datetime.now().time()
            
            # If we haven't recorded last reset or it's past reset time
            if self.last_reset_time is None:
                return True
            
            last_reset_date = self.last_reset_time.date()
            current_date = datetime.now().date()
            
            # New day and we've passed the reset time
            if current_date > last_reset_date and current_time >= reset_time:
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error checking reset time: {e}")
            return False

    def update_drawdown_tracking(self, current_equity: float) -> Tuple[float, float, bool]:
        """
        Update drawdown tracking and check if kill switch should activate.
        
        Args:
            current_equity: Current account equity
            
        Returns:
            Tuple of (daily_drawdown_percent, intraday_drawdown_percent, kill_switch_triggered)
        """
        # Reset daily tracking if needed
        if self.should_reset_daily_drawdown():
            self.daily_start_equity = current_equity
            self.session_peak_equity = current_equity
            self.last_reset_time = datetime.now()
            self.kill_switch_active = False
            logger.info(f"Daily drawdown reset - New daily equity: ${current_equity:,.2f}")

        # Update session peak
        if current_equity > self.session_peak_equity:
            self.session_peak_equity = current_equity

        # Calculate drawdowns
        daily_drawdown = self._calculate_drawdown(
            current_equity, 
            self.daily_start_equity
        )
        intraday_drawdown = self._calculate_drawdown(
            current_equity, 
            self.session_peak_equity
        )

        # Check kill switch conditions
        kill_switch_triggered = False
        
        if daily_drawdown >= self.max_daily_drawdown:
            if not self.kill_switch_active:
                self._activate_kill_switch(daily_drawdown, "DAILY")
                kill_switch_triggered = True
            self.kill_switch_active = True
            
        elif intraday_drawdown >= self.max_intraday_drawdown:
            if not self.kill_switch_active:
                self._activate_kill_switch(intraday_drawdown, "INTRADAY")
                kill_switch_triggered = True
            self.kill_switch_active = True

        # Check alert thresholds (before kill switch activates)
        if self.enable_drawdown_alerts and not self.kill_switch_active:
            self._check_alert_thresholds(daily_drawdown, intraday_drawdown)

        return daily_drawdown, intraday_drawdown, kill_switch_triggered

    def _calculate_drawdown(self, current_equity: float, reference_equity: float) -> float:
        """
        Calculate drawdown percentage.
        
        Args:
            current_equity: Current equity
            reference_equity: Reference equity (peak or session start)
            
        Returns:
            Drawdown as decimal (0-1)
        """
        if reference_equity <= 0:
            return 0
        
        drawdown = (reference_equity - current_equity) / reference_equity
        return max(0, drawdown)

    def _activate_kill_switch(self, drawdown_amount: float, drawdown_type: str) -> None:
        """
        Log and activate kill switch with specified action.
        
        Args:
            drawdown_amount: Current drawdown percentage
            drawdown_type: "DAILY" or "INTRADAY"
        """
        logger.critical(
            f"⚠️  KILL SWITCH ACTIVATED - {drawdown_type} DRAWDOWN: {drawdown_amount*100:.2f}%"
        )
        logger.critical(f"Kill Switch Mode: {self.kill_switch_mode}")
        
        if self.kill_switch_mode == "STOP_OPENING":
            logger.critical("🛑 Bot will STOP OPENING new positions but manage existing ones")
        elif self.kill_switch_mode == "PAUSE_TRADING":
            logger.critical("🛑 Bot PAUSING ALL TRADING")
        elif self.kill_switch_mode == "EMERGENCY_CLOSE":
            logger.critical("🛑 Bot CLOSING ALL POSITIONS IMMEDIATELY")

    def _check_alert_thresholds(self, daily_dd: float, intraday_dd: float) -> None:
        """
        Check if drawdown is approaching limits and trigger alerts.
        
        Args:
            daily_dd: Daily drawdown percentage
            intraday_dd: Intraday drawdown percentage
        """
        daily_percent = daily_dd * 100
        intraday_percent = intraday_dd * 100
        max_daily_percent = self.max_daily_drawdown * 100
        max_intraday_percent = self.max_intraday_drawdown * 100
        
        for threshold_pct in self.drawdown_alert_thresholds:
            daily_threshold = (threshold_pct / 100) * max_daily_percent
            intraday_threshold = (threshold_pct / 100) * max_intraday_percent
            
            # Daily drawdown alert
            daily_alert_key = f"daily_{threshold_pct}"
            if daily_dd >= daily_threshold and daily_alert_key not in self.alerts_triggered:
                logger.warning(
                    f"⚠️  DRAWDOWN ALERT: Daily drawdown {daily_percent:.2f}% "
                    f"({threshold_pct}% of {max_daily_percent:.1f}% limit)"
                )
                self.alerts_triggered[daily_alert_key] = True
            
            # Intraday drawdown alert
            intraday_alert_key = f"intraday_{threshold_pct}"
            if intraday_dd >= intraday_threshold and intraday_alert_key not in self.alerts_triggered:
                logger.warning(
                    f"⚠️  DRAWDOWN ALERT: Intraday drawdown {intraday_percent:.2f}% "
                    f"({threshold_pct}% of {max_intraday_percent:.1f}% limit)"
                )
                self.alerts_triggered[intraday_alert_key] = True

    def can_open_position(self, current_equity: float, current_positions: int) -> Tuple[bool, str]:
        """
        Determine if new positions can be opened based on risk limits.
        
        Args:
            current_equity: Current account equity
            current_positions: Number of currently open positions
            
        Returns:
            Tuple of (can_open: bool, reason: str)
        """
        # Check kill switch
        if self.kill_switch_active:
            if self.kill_switch_mode == "STOP_OPENING":
                return False, f"Kill switch active ({self.kill_switch_mode})"
            elif self.kill_switch_mode == "PAUSE_TRADING":
                return False, "Kill switch active (PAUSE_TRADING)"
            elif self.kill_switch_mode == "EMERGENCY_CLOSE":
                return False, "Kill switch active (EMERGENCY_CLOSE)"
        
        # Check position limits
        if current_positions >= self.max_concurrent_positions:
            return False, f"Max concurrent positions reached ({self.max_concurrent_positions})"
        
        return True, "OK"

    def can_open_symbol_position(
        self, 
        symbol: str, 
        symbol_positions: int
    ) -> Tuple[bool, str]:
        """
        Check if another position can be opened for a specific symbol.
        
        Args:
            symbol: Trading symbol
            symbol_positions: Number of positions already open for this symbol
            
        Returns:
            Tuple of (can_open: bool, reason: str)
        """
        if symbol_positions >= self.max_positions_per_symbol:
            return False, f"Max positions for {symbol} reached ({self.max_positions_per_symbol})"
        
        return True, "OK"

    def get_risk_summary(self, current_equity: float) -> Dict:
        """
        Get comprehensive risk summary.
        
        Args:
            current_equity: Current account equity
            
        Returns:
            Dictionary with risk metrics
        """
        daily_dd, intraday_dd, _ = self.update_drawdown_tracking(current_equity)
        
        return {
            'session_start_equity': self.session_start_equity,
            'session_peak_equity': self.session_peak_equity,
            'daily_start_equity': self.daily_start_equity,
            'current_equity': current_equity,
            'daily_drawdown_percent': daily_dd * 100,
            'intraday_drawdown_percent': intraday_dd * 100,
            'max_daily_drawdown_limit': self.max_daily_drawdown * 100,
            'max_intraday_drawdown_limit': self.max_intraday_drawdown * 100,
            'kill_switch_active': self.kill_switch_active,
            'kill_switch_mode': self.kill_switch_mode,
            'max_concurrent_positions': self.max_concurrent_positions,
            'max_positions_per_symbol': self.max_positions_per_symbol
        }

    def reset_alerts(self) -> None:
        """Reset alert triggers for a new session."""
        self.alerts_triggered = {}
        logger.debug("Alert triggers reset")
