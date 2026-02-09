# ═══════════════════════════════════════════════════════════════════════════
# BENNER BOT v4.1 - INTEGRATION EXAMPLE
# Shows how to integrate RiskManager and SessionManager into your bot
# ═══════════════════════════════════════════════════════════════════════════

"""
This file shows the KEY INTEGRATION POINTS where you should add the new
risk management and session controls to your existing bot.

The actual bot file is likely much longer - this shows the essential parts.
"""

import logging
import MetaTrader5 as mt5
from datetime import datetime
from typing import List, Dict

# NEW IMPORTS for v4.1
from risk_manager import RiskManager
from trading_session_manager import TradingSessionManager
from config_loader import load_config

logger = logging.getLogger(__name__)


class BennerBotV41:
    """
    Benner Trading Bot v4.1 with Risk Management and Session Controls
    """
    
    def __init__(self):
        """Initialize bot with all components."""
        
        # Load configuration from .env
        self.config = load_config()
        
        # EXISTING COMPONENTS (your current bot)
        self.account_info = None
        self.positions = []
        self.pending_orders = []
        
        # NEW v4.1 COMPONENTS ✨
        self.risk_manager = RiskManager(self.config)
        self.session_manager = TradingSessionManager(self.config)
        
        logger.info("BennerBotV41 initialized with risk management and session controls")
    
    def start_trading_session(self):
        """
        Initialize trading session - called once when bot starts.
        """
        # Connect to MetaTrader 5
        if not mt5.initialize():
            logger.error("Failed to initialize MT5")
            return False
        
        # Get account info
        account = mt5.account_info()
        if account is None:
            logger.error("Failed to get account info")
            return False
        
        # INITIALIZE RISK MANAGER (new in v4.1)
        self.risk_manager.initialize_session(account.balance)
        
        logger.info(f"Trading session started")
        logger.info(f"Account: {account.name}")
        logger.info(f"Balance: ${account.balance:,.2f}")
        logger.info(f"Equity: ${account.equity:,.2f}")
        
        return True
    
    def trading_cycle(self):
        """
        Main trading cycle - called repeatedly (every UPDATE_INTERVAL seconds).
        
        NEW in v4.1:
        - Risk tracking
        - Kill switch enforcement
        - Session-aware symbol selection
        - Position limits
        """
        
        try:
            # Get current account state
            account = mt5.account_info()
            if account is None:
                logger.error("Failed to get account info")
                return
            
            current_equity = account.equity
            current_balance = account.balance
            
            # ════════════════════════════════════════════════════════════════════
            # STEP 1: UPDATE RISK TRACKING (NEW in v4.1) ✨
            # ════════════════════════════════════════════════════════════════════
            
            daily_dd, intraday_dd, kill_switch_triggered = \
                self.risk_manager.update_drawdown_tracking(current_equity)
            
            # Log risk status
            logger.info("=" * 70)
            logger.info("RISK STATUS UPDATE")
            logger.info(f"  Current Equity: ${current_equity:,.2f}")
            logger.info(f"  Daily Drawdown: {daily_dd*100:.2f}% "
                       f"(Limit: {self.risk_manager.max_daily_drawdown*100:.1f}%)")
            logger.info(f"  Intraday Drawdown: {intraday_dd*100:.2f}% "
                       f"(Limit: {self.risk_manager.max_intraday_drawdown*100:.1f}%)")
            logger.info(f"  Kill Switch Active: {self.risk_manager.kill_switch_active}")
            
            if kill_switch_triggered:
                logger.critical("⚠️  KILL SWITCH JUST ACTIVATED!")
            
            # ════════════════════════════════════════════════════════════════════
            # STEP 2: GET TRADEABLE SYMBOLS (NEW in v4.1) ✨
            # ════════════════════════════════════════════════════════════════════
            
            # Get all configured symbols
            all_mean_reversion_symbols = \
                self.config['MEAN_REVERSION_SYMBOLS'].split(',')
            
            # Filter to only TRADEABLE symbols based on sessions
            tradeable_symbols = \
                self.session_manager.get_active_tradeable_symbols(
                    all_mean_reversion_symbols
                )
            
            logger.info(f"Tradeable symbols this cycle: {tradeable_symbols}")
            
            # Show which symbols are NOT tradeable (for monitoring)
            skipped_symbols = set(all_mean_reversion_symbols) - set(tradeable_symbols)
            if skipped_symbols:
                for symbol in skipped_symbols:
                    can_trade, reason = self.session_manager.can_trade_symbol(symbol)
                    logger.info(f"  ⏸️  {symbol}: {reason}")
            
            # ════════════════════════════════════════════════════════════════════
            # STEP 3: COUNT CURRENT POSITIONS (needed for risk checks)
            # ════════════════════════════════════════════════════════════════════
            
            current_positions = self._count_open_positions()
            logger.info(f"Current open positions: {current_positions}")
            
            # ════════════════════════════════════════════════════════════════════
            # STEP 4: PROCESS EACH TRADEABLE SYMBOL
            # ════════════════════════════════════════════════════════════════════
            
            for symbol in tradeable_symbols:
                logger.info(f"\n--- Processing {symbol} ---")
                
                # Step 4a: Generate trading signal
                signal = self.signal_generator.analyze(symbol)
                if signal['action'] == 'HOLD':
                    logger.info(f"{symbol}: No signal (HOLD)")
                    self._check_exit_conditions(symbol)
                    continue
                
                logger.info(f"{symbol}: Signal = {signal['action']} "
                           f"(Tier {signal.get('tier', '?')}) - {signal.get('reason', '')}")
                
                # Step 4b: Check GLOBAL position limit (NEW in v4.1)
                can_open, reason = self.risk_manager.can_open_position(
                    current_equity,
                    current_positions
                )
                
                if not can_open:
                    logger.warning(f"  ❌ Cannot open position: {reason}")
                    continue
                
                # Step 4c: Check SYMBOL-SPECIFIC position limit (NEW in v4.1)
                symbol_positions = self._count_positions_for_symbol(symbol)
                can_open_symbol, reason = \
                    self.risk_manager.can_open_symbol_position(
                        symbol,
                        symbol_positions
                    )
                
                if not can_open_symbol:
                    logger.warning(f"  ❌ Cannot open {symbol} position: {reason}")
                    continue
                
                # Step 4d: All checks passed - OPEN POSITION
                logger.info(f"  ✅ Opening {signal['action']} position for {symbol}")
                
                self._open_position(symbol, signal)
                current_positions += 1  # Update local count
                
                # Step 4e: Manage existing positions (take profit, stop loss)
                self._check_exit_conditions(symbol)
            
            # ════════════════════════════════════════════════════════════════════
            # STEP 5: LOG COMPREHENSIVE SUMMARY
            # ════════════════════════════════════════════════════════════════════
            
            self._log_cycle_summary(current_equity, current_balance, 
                                   current_positions, tradeable_symbols)
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
    
    def _count_open_positions(self) -> int:
        """Count total number of open positions."""
        positions = mt5.positions_get()
        return len(positions) if positions else 0
    
    def _count_positions_for_symbol(self, symbol: str) -> int:
        """Count open positions for a specific symbol."""
        positions = mt5.positions_get(symbol=symbol)
        return len(positions) if positions else 0
    
    def _open_position(self, symbol: str, signal: Dict):
        """
        Open a new trading position.
        
        This is your existing position opening logic.
        Just needs to be called from the trading cycle with proper checks.
        """
        # Your existing position opening code here
        # Example:
        # lot = self.calculate_lot_size(symbol, signal['tier'])
        # price = self._get_entry_price(symbol, signal)
        # request = {...}
        # result = mt5.order_send(request)
        pass
    
    def _check_exit_conditions(self, symbol: str):
        """
        Check and manage existing positions for take profit / stop loss.
        
        This is your existing position management logic.
        Should be called for both open and closed signal periods.
        """
        # Your existing exit management code here
        pass
    
    def _log_cycle_summary(self, equity: float, balance: float, 
                          positions: int, tradeable_symbols: List[str]):
        """
        Log comprehensive cycle summary for monitoring.
        """
        risk_summary = self.risk_manager.get_risk_summary(equity)
        session_summary = self.session_manager.get_session_summary()
        
        logger.info("\n" + "=" * 70)
        logger.info("CYCLE SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"\nACCOUNT:")
        logger.info(f"  Balance: ${balance:,.2f}")
        logger.info(f"  Equity: ${equity:,.2f}")
        logger.info(f"  Daily DD: {risk_summary['daily_drawdown_percent']:.2f}% "
                   f"/ {risk_summary['max_daily_drawdown_limit']:.1f}%")
        logger.info(f"  Intraday DD: {risk_summary['intraday_drawdown_percent']:.2f}% "
                   f"/ {risk_summary['max_intraday_drawdown_limit']:.1f}%")
        logger.info(f"\nPOSITIONS:")
        logger.info(f"  Open: {positions} / {risk_summary['max_concurrent_positions']}")
        logger.info(f"  Max per symbol: {risk_summary['max_positions_per_symbol']}")
        logger.info(f"  Kill Switch: {risk_summary['kill_switch_active']}")
        logger.info(f"\nTRADEABLE SYMBOLS:")
        logger.info(f"  {tradeable_symbols}")
        logger.info("=" * 70 + "\n")
    
    def stop_trading_session(self):
        """
        Stop trading session - called when bot shuts down.
        """
        # Get final summary
        account = mt5.account_info()
        if account:
            logger.info(f"Final Account State:")
            logger.info(f"  Balance: ${account.balance:,.2f}")
            logger.info(f"  Equity: ${account.equity:,.2f}")
        
        # Shutdown MT5
        mt5.shutdown()
        logger.info("Trading session ended")


# ═══════════════════════════════════════════════════════════════════════════
# EXAMPLE: MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main bot execution."""
    
    # Initialize logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('benner_bot_v4.1.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create bot instance
    bot = BennerBotV41()
    
    # Start trading session
    if not bot.start_trading_session():
        logger.error("Failed to start trading session")
        return
    
    # Main loop
    update_interval = int(bot.config.get('UPDATE_INTERVAL', 60))
    
    try:
        while True:
            bot.trading_cycle()
            
            # Wait for next cycle
            import time
            time.sleep(update_interval)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        bot.stop_trading_session()


if __name__ == '__main__':
    main()


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════

"""
✅ Import new modules (RiskManager, SessionManager, etc.)
✅ Initialize RiskManager and SessionManager in __init__
✅ Call risk_manager.initialize_session() at bot startup
✅ Call risk_manager.update_drawdown_tracking() each cycle
✅ Call session_manager.get_active_tradeable_symbols() to filter symbols
✅ Call risk_manager.can_open_position() before opening positions
✅ Call risk_manager.can_open_symbol_position() for per-symbol limits
✅ Only process tradeable symbols (from session manager)
✅ Log comprehensive summaries for monitoring
✅ Test with DRY_RUN=True first

EXPECTED BEHAVIOR CHANGES:

Before v4.1:
  - Opened positions on all symbols regardless of time/liquidity
  - No drawdown limits (could lose 50%+ in single day)
  - Attempted forex trading on weekends
  - Would open unlimited positions

After v4.1:
  - Opens positions only on symbols in active sessions
  - Stops at configurable drawdown limit (default 30%)
  - Respects market hours (forex closed weekends, crypto 24/7)
  - Limits concurrent positions to prevent over-leveraging
  - Smarter symbol selection based on liquidity
"""
