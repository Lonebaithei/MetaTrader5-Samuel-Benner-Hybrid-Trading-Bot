# ═══════════════════════════════════════════════════════════════════════════
# BENNER BOT v4.1 - QUICK START GUIDE
# Common Configurations & Troubleshooting
# ═══════════════════════════════════════════════════════════════════════════

## QUICK SETUP (5 MINUTES)

### 1. Copy Configuration Template
```bash
cp .env.v4.1.example .env
```

### 2. Edit Key Settings
```bash
# Edit .env file with these essential settings:

# Your MT5 credentials
MT5_LOGIN=your_login
MT5_PASSWORD=your_password
MT5_SERVER=your_server

# Risk limits (CRITICAL!)
MAX_DAILY_DRAWDOWN_PERCENT=30        # Stop at 30% loss
MAX_INTRADAY_DRAWDOWN_PERCENT=20     # Stop at 20% loss
MAX_CONCURRENT_POSITIONS=5            # Max 5 open positions
MAX_POSITIONS_PER_SYMBOL=2            # Max 2 per symbol

# Enable session controls
ENABLE_TRADING_SESSIONS=True
ENABLE_AUTO_MARKET_HOURS_DETECTION=True

# Crypto trading (24/7)
CRYPTO_TRADE_WEEKENDS=True
```

### 3. Run Bot
```bash
python benner_bot_v4.1.py
```

---

## CONFIGURATION PROFILES 🎯

Choose the one that matches your trading style:

### CONSERVATIVE (Smaller Account)
```bash
# File: .env.conservative

# Strict risk limits
MAX_DAILY_DRAWDOWN_PERCENT=15        # Tight limit
MAX_INTRADAY_DRAWDOWN_PERCENT=10
MAX_CONCURRENT_POSITIONS=3            # Very few positions
MAX_POSITIONS_PER_SYMBOL=1            # One per symbol only
RISK_PER_TRADE_PERCENT=0.01           # 1% per trade

# Use all safety features
ENABLE_TRADING_SESSIONS=True
ENABLE_AUTO_MARKET_HOURS_DETECTION=True
CRYPTO_TRADE_WEEKENDS=False           # Skip weekends

# Alert early
ENABLE_DRAWDOWN_ALERTS=True
KILL_SWITCH_MODE=PAUSE_TRADING        # Stop all trading
```

### MODERATE (Medium Account) ⭐ RECOMMENDED
```bash
# File: .env.moderate

# Balanced risk/reward
MAX_DAILY_DRAWDOWN_PERCENT=25
MAX_INTRADAY_DRAWDOWN_PERCENT=15
MAX_CONCURRENT_POSITIONS=5            # Standard 5
MAX_POSITIONS_PER_SYMBOL=2            # Up to 2 per symbol
RISK_PER_TRADE_PERCENT=0.02           # 2% per trade

# Use safety features
ENABLE_TRADING_SESSIONS=True
ENABLE_AUTO_MARKET_HOURS_DETECTION=True
CRYPTO_TRADE_WEEKENDS=True            # Trade crypto weekends

# Reasonable alerts
ENABLE_DRAWDOWN_ALERTS=True
KILL_SWITCH_MODE=STOP_OPENING         # Stop new positions only
```

### AGGRESSIVE (Larger Account)
```bash
# File: .env.aggressive

# Higher risk tolerance
MAX_DAILY_DRAWDOWN_PERCENT=35
MAX_INTRADAY_DRAWDOWN_PERCENT=25
MAX_CONCURRENT_POSITIONS=8            # More positions
MAX_POSITIONS_PER_SYMBOL=3            # Up to 3 per symbol
RISK_PER_TRADE_PERCENT=0.05           # 5% per trade

# Still use safety features
ENABLE_TRADING_SESSIONS=True
ENABLE_AUTO_MARKET_HOURS_DETECTION=False  # Rely on manual times
CRYPTO_TRADE_WEEKENDS=True

# Relaxed alerts
ENABLE_DRAWDOWN_ALERTS=True
KILL_SWITCH_MODE=STOP_OPENING
```

---

## COMMON SCENARIOS 📋

### Scenario 1: "I want to trade only European hours"
```bash
# Only trade during Europe/US overlap (tightest spreads)

ENABLE_TRADING_SESSIONS=True

# Disable Asian session
FOREX_ASIA_SESSION_START=
FOREX_ASIA_SESSION_END=

# Keep Europe and America
FOREX_EUROPE_SESSION_START=08:00
FOREX_EUROPE_SESSION_END=17:00

FOREX_AMERICA_SESSION_START=13:00
FOREX_AMERICA_SESSION_END=22:00

# Only trade EURUSD, GBPUSD during these times
MEAN_REVERSION_SYMBOLS=EURUSD,GBPUSD
```

### Scenario 2: "I want 24/7 crypto trading only"
```bash
# Trade only crypto which is 24/7

# Disable forex sessions
FOREX_ASIA_SESSION_START=
FOREX_ASIA_SESSION_END=
FOREX_EUROPE_SESSION_START=
FOREX_EUROPE_SESSION_END=
FOREX_AMERICA_SESSION_START=
FOREX_AMERICA_SESSION_END=

# Keep crypto
CRYPTO_TRADE_WEEKENDS=True
CRYPTO_SESSION_START=00:00
CRYPTO_SESSION_END=23:59

# Only trade crypto
MEAN_REVERSION_SYMBOLS=BTCUSD,ETHUSD
```

### Scenario 3: "I lost $1000, don't want this to happen again"
```bash
# Much stricter limits after losing money

# Drop daily limit from 30% to 15%
MAX_DAILY_DRAWDOWN_PERCENT=15

# Drop positions from 5 to 3
MAX_CONCURRENT_POSITIONS=3

# Drop per-symbol from 2 to 1
MAX_POSITIONS_PER_SYMBOL=1

# Kill switch in aggressive mode
KILL_SWITCH_MODE=PAUSE_TRADING

# Trade less frequently (longer update interval)
UPDATE_INTERVAL=300  # Check every 5 minutes instead of 1

# Trade only best hours
ENABLE_TRADING_SESSIONS=True
ENABLE_AUTO_MARKET_HOURS_DETECTION=True
```

### Scenario 4: "I want to maximize weekend crypto profits"
```bash
# Aggressive crypto weekend trading

CRYPTO_TRADE_WEEKENDS=True
CRYPTO_SESSION_START=00:00
CRYPTO_SESSION_END=23:59

# Reasonable position limits
MAX_CONCURRENT_POSITIONS=5
MAX_POSITIONS_PER_SYMBOL=2

# Standard risk
MAX_DAILY_DRAWDOWN_PERCENT=30
MAX_INTRADAY_DRAWDOWN_PERCENT=20

# Only crypto
MEAN_REVERSION_SYMBOLS=BTCUSD,ETHUSD,LTCUSD

# Faster updates on weekends
UPDATE_INTERVAL=30  # Check every 30 seconds
```

---

## TROUBLESHOOTING 🔧

### Problem: "Bot not opening any positions"

**Check 1: Kill Switch Active?**
```bash
# Look in logs for:
"Kill switch active (STOP_OPENING)"

# If yes:
  - Your drawdown hit the limit
  - Check your MAX_DAILY_DRAWDOWN_PERCENT setting
  - Or reset time if it should have reset already
```

**Check 2: No Tradeable Symbols?**
```bash
# Look in logs for:
"⏸️  EURUSD: Outside trading session"

# If yes, your symbol isn't in an active session
# Options:
  1. Check if session time is correct (in UTC!)
  2. Disable ENABLE_TRADING_SESSIONS=False temporarily to test
  3. Add more session times to match your market
```

**Check 3: Position Limits Hit?**
```bash
# Look in logs for:
"Max concurrent positions reached (5/5)"

# If yes:
  - Close some existing positions, OR
  - Increase MAX_CONCURRENT_POSITIONS, OR
  - Wait for existing positions to close
```

**Check 4: Symbol-Specific Limit Hit?**
```bash
# Look in logs for:
"Max positions for EURUSD reached (2/2)"

# If yes:
  - This symbol already has max positions
  - Close one position for this symbol, OR
  - Increase MAX_POSITIONS_PER_SYMBOL
```

---

### Problem: "Kill switch triggered after small loss"

**Cause:** MAX_DAILY_DRAWDOWN_PERCENT is too low

**Example:**
```bash
Account: $10,000
MAX_DAILY_DRAWDOWN_PERCENT=10  # Only $1,000 allowed

After 3 losing trades: -$1,200
Drawdown: 12% > Limit 10%
Result: Kill switch triggered!

Solution: Increase to 20-30%
MAX_DAILY_DRAWDOWN_PERCENT=25  # $2,500 allowed
```

---

### Problem: "EURUSD not trading but it's during European session"

**Possible Causes:**

1. **Your timezone not UTC**
   ```bash
   # You think it's 15:00 your time (European hours)
   # But in UTC it's 22:00 (American session)
   # EURUSD might already be past European hours
   
   Solution: Use UTC times always!
   Check: https://www.timeanddate.com/worldclock/utc
   ```

2. **Auto market hours detection blocking**
   ```bash
   # Bid-ask spread too wide, market considered closed
   # Check logs for: "Low liquidity (spread: X pips)"
   
   Solution:
   Option A: Increase LIQUIDITY_MIN_SPREAD_THRESHOLD
     # Current: 2 pips
     # Try: 3 or 4 pips
   
   Option B: Disable auto detection
     ENABLE_AUTO_MARKET_HOURS_DETECTION=False
   ```

3. **Session times wrong**
   ```bash
   # Check the actual trading hours for your broker
   # Example: Your broker might have different hours than standard
   
   Solution:
   # Test with market hours detection on
   ENABLE_AUTO_MARKET_HOURS_DETECTION=True
   # This queries the broker API for actual market hours
   ```

---

### Problem: "Bot trading crypto on weekend with low volume"

**If you want to skip weekends:**
```bash
CRYPTO_TRADE_WEEKENDS=False  # Don't trade crypto on weekends
```

**If you want to trade but with smaller positions:**
```bash
# Keep trading weekends
CRYPTO_TRADE_WEEKENDS=True

# But reduce risk on weekends
MAX_POSITIONS_PER_SYMBOL=1  # Only 1 position on weekend crypto

# Or reduce per-trade risk
RISK_PER_TRADE_PERCENT=0.01  # 1% instead of 2%
```

---

## MONITORING YOUR BOT 📊

### Key Metrics to Watch

**Every hour, check:**
```
✅ Equity trending up or down?
✅ Daily drawdown < 50% of limit?
✅ Concurrent positions < 80% of max?
✅ Kill switch NOT active?
```

**Every day:**
```
✅ Total P&L positive?
✅ Win rate > 40%? (for mean reversion)
✅ Daily drawdown not exceeding 10%?
✅ No unexpected API errors?
```

### Reading the Logs

**GOOD LOG OUTPUT:**
```
2026-02-09 14:35:45 - RISK STATUS UPDATE
  Current Equity: $10,250.00
  Daily Drawdown: 2.50% (Limit: 30.0%)
  Intraday Drawdown: -0.10% (Limit: 20.0%)
  Kill Switch Active: False

--- Processing EURUSD ---
EURUSD: Signal = BUY (Tier 1) - TIER 1 Extreme Oversold
  ✅ Opening BUY position for EURUSD

Tradeable symbols this cycle: [EURUSD, XAUUSD, BTCUSD]
```

**PROBLEM LOG OUTPUT:**
```
⚠️  DRAWDOWN ALERT: Daily drawdown 22.5%
(75% of 30.0% limit)

🛑 KILL SWITCH ACTIVATED - DAILY DRAWDOWN: 30.00%
Kill Switch Mode: STOP_OPENING

--- Processing EURUSD ---
  ❌ Cannot open position: Kill switch active (STOP_OPENING)
```

---

## PERFORMANCE TUNING ⚡

### To Trade More (Generate More Opportunities)
```bash
# Reduce session restrictions
ENABLE_TRADING_SESSIONS=False      # Trade all the time

# Increase position limits
MAX_CONCURRENT_POSITIONS=10        # More open trades
MAX_POSITIONS_PER_SYMBOL=3         # More per symbol

# Check more frequently
UPDATE_INTERVAL=15                 # Check every 15 sec

# Increase daily limit
MAX_DAILY_DRAWDOWN_PERCENT=40      # More room to lose
```

### To Trade Less (Reduce Losses)
```bash
# Strict session control
ENABLE_TRADING_SESSIONS=True                    # Use sessions
ENABLE_AUTO_MARKET_HOURS_DETECTION=True        # Double-check

# Reduce position limits
MAX_CONCURRENT_POSITIONS=2         # Fewer trades
MAX_POSITIONS_PER_SYMBOL=1         # One per symbol

# Check less frequently
UPDATE_INTERVAL=300                # Check every 5 min

# Strict daily limit
MAX_DAILY_DRAWDOWN_PERCENT=15      # Stop quickly
```

---

## REAL EXAMPLE: MY RECOMMENDED SETTINGS 🌟

### For $5,000 Account (Beginner)
```bash
# Risk management (safe)
MAX_DAILY_DRAWDOWN_PERCENT=20      # $1,000 max loss/day
MAX_INTRADAY_DRAWDOWN_PERCENT=12
MAX_CONCURRENT_POSITIONS=3
MAX_POSITIONS_PER_SYMBOL=1
RISK_PER_TRADE_PERCENT=0.02        # 2% risk per trade

# Session control (smart)
ENABLE_TRADING_SESSIONS=True
ENABLE_AUTO_MARKET_HOURS_DETECTION=True
CRYPTO_TRADE_WEEKENDS=True

# Alerts (active monitoring)
ENABLE_DRAWDOWN_ALERTS=True
KILL_SWITCH_MODE=STOP_OPENING

# Trading symbols (focus)
MEAN_REVERSION_SYMBOLS=EURUSD,GBPUSD,XAUUSD
UPDATE_INTERVAL=60                 # Check every 1 min
```

### For $50,000 Account (Advanced)
```bash
# Risk management (balanced)
MAX_DAILY_DRAWDOWN_PERCENT=30      # $15,000 max loss/day
MAX_INTRADAY_DRAWDOWN_PERCENT=20
MAX_CONCURRENT_POSITIONS=8
MAX_POSITIONS_PER_SYMBOL=2
RISK_PER_TRADE_PERCENT=0.05        # 5% risk per trade

# Session control (optimized)
ENABLE_TRADING_SESSIONS=True
ENABLE_AUTO_MARKET_HOURS_DETECTION=False  # Manual times OK
CRYPTO_TRADE_WEEKENDS=True

# Alerts (selective)
ENABLE_DRAWDOWN_ALERTS=True
KILL_SWITCH_MODE=STOP_OPENING

# Trading symbols (expanded)
MEAN_REVERSION_SYMBOLS=EURUSD,GBPUSD,XAUUSD,USDJPY,AUDUSD,BTCUSD
UPDATE_INTERVAL=30                 # Check every 30 sec
```

---

## QUICK TEST (Before Live Trading!)

```bash
# Set to dry run mode
DRY_RUN=True

# Set conservative limits
MAX_DAILY_DRAWDOWN_PERCENT=15
MAX_CONCURRENT_POSITIONS=3

# Run for 2-3 days
# Check logs for:
#  ✅ Signals generating
#  ✅ Positions opening/closing
#  ✅ Risk tracking working
#  ✅ Session filtering working
#  ✅ No errors

# If all good, set DRY_RUN=False
# Start with 1-2 day live trading
# Monitor drawdown closely
# Increase limits only after consistent profitability
```

---

## SUPPORT & DEBUGGING 🚀

### Enable Debug Logging
```bash
# In .env:
LOG_LEVEL=DEBUG

# This will log EVERYTHING including:
# - Cache operations
# - API calls
# - Decision logic
# - Full risk calculations
```

### Export Logs for Analysis
```bash
# Helpful for debugging
tail -n 1000 benner_bot_v4.1.log | grep "EURUSD"
grep "Kill Switch" benner_bot_v4.1.log
grep "WARNING\|ERROR" benner_bot_v4.1.log
```

---

## SUMMARY ✅

1. **Copy .env.v4.1.example to .env**
2. **Edit with your settings (use a profile above)**
3. **Test with DRY_RUN=True for 1-2 days**
4. **Monitor drawdown and position limits closely**
5. **Start live with conservative settings**
6. **Gradually increase limits as you gain confidence**

**Remember:** The goal is not to make the most money, but to make consistent money while protecting your capital. These settings help you do that!

---

**Questions? Check the IMPLEMENTATION_GUIDE_v4.1.md file for more detailed explanations.**
