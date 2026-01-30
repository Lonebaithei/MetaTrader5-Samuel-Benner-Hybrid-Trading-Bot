# 🚀 Benner Trading Bot v3.0 - Complete Setup Guide

## 📋 **Table of Contents**

1. [What's New in v3.0](#whats-new-in-v30)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [First Run](#first-run)
6. [Features Guide](#features-guide)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## 🎉 **What's New in v3.0**

### **Critical Fixes:**
✅ **Security:** No more hardcoded passwords! Uses environment variables  
✅ **Weekend Check:** Won't try to trade when Forex market is closed  
✅ **Total Exposure:** Prevents over-leveraging (max 30% exposure)  
✅ **Correlation Risk:** Won't open highly correlated positions  
✅ **Dry-Run Mode:** Test safely without risking real money  
✅ **Leverage Fix:** Uses actual account leverage, not hardcoded  

### **New Features:**
🎯 **Performance Tracking:** Win rate, profit factor, trade history  
📊 **Trade Journal:** CSV export of all trades  
📱 **Telegram Alerts:** Get notified of trades on your phone  
🔄 **Trailing Stops:** Automatically lock in profits  
📈 **Risk Manager:** Smart exposure and correlation management  
📝 **Log Rotation:** Prevents log files from growing infinitely  
⚡ **Multi-Strategy Magic Numbers:** Track performance by strategy  

---

## 💻 **System Requirements**

### **Minimum:**
- **OS:** Windows 10/11, Linux, or macOS
- **Python:** 3.8+
- **RAM:** 4GB
- **MT5:** MetaTrader 5 terminal installed
- **Internet:** Stable connection

### **Recommended:**
- **Python:** 3.10+
- **RAM:** 4-8GB+
- **SSD:** For faster data access

---

## 📦 **Installation**

### **Step 1: Install Python Packages**

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install all required packages
pip install MetaTrader5 pandas numpy yfinance python-dotenv requests
```

### **Step 2: Download Bot Files**

You should have these files:
```
benner_bot_v3/
├── benner_bot_v3.py          # Main bot (combined Part 1, 2, 3)
├── .env.template              # Configuration template
└── README.md                  # This file
```

### **Step 3: Combine the Code Files**

**IMPORTANT:** The bot code was split into 3 parts, and were combined for you.

1. The main bot file : `benner_bot_v3.py` made up of;
2. Copy Part 1 (up to MarketDataProvider)
3. Append Part 2 (MarketRegime through PositionManager)
4. Append Part 3 (BennerTradingBot and main())

---

## ⚙️ **Configuration**

### **Step 1: Create .env File**

```bash
# Copy the template
cp .env.template .env

# Edit with your values
nano .env  # or use any text editor
```

### **Step 2: Fill in Your MT5 Credentials**

```bash
# .env file contents:
MT5_LOGIN=5987063                    # Your MT5 account number
MT5_PASSWORD=your_actual_password    # Your MT5 password
MT5_SERVER=Deriv-Demo                # Your broker's server name
DRY_RUN=True                         # Keep True for testing!
```

**How to find your MT5 server:**
1. Open MetaTrader 5
2. Click on your account number at the top
3. The server name is shown in account details (e.g., "Deriv-Demo", "Exness-MT5Trial7")

### **Step 3: (Optional) Setup Telegram Alerts**

**Getting a Bot Token:**
1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Follow instructions
5. Copy the token you receive

**Getting Your Chat ID:**
1. Search for `@userinfobot` on Telegram
2. Start a chat
3. It will send you your chat ID
4. Copy it

**Add to .env:**
```bash
TELEGRAM_ENABLED=True
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

---

## 🎬 **First Run**

### **Pre-Flight Checklist:**

- [ ] MT5 is installed and running
- [ ] MT5 is logged into your account
- [ ] Automated trading is enabled in MT5:
  - Tools → Options → Expert Advisors
  - Check "Allow automated trading"
- [ ] `.env` file exists with your credentials
- [ ] `DRY_RUN=True` in `.env` (for testing)

### **Run the Bot:**

```bash
# Make sure MT5 is running first!

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Run the bot
python benner_bot_v3.py
```

### **What You Should See:**

```
================================================================================
BENNER TRADING BOT v3.0 - ENTERPRISE EDITION
================================================================================

DRY RUN MODE: True
⚠️  DRY RUN MODE ENABLED - No real trades will be executed!

[SUCCESS] Connected to MT5 account: 5987063
Account Balance: $10,000.00 | Equity: $10,000.00

[SYMBOL AVAILABILITY CHECK]
✓ EURUSD: Available (Min: 0.01, Max: 100.0)
✓ USDJPY: Available (Min: 0.01, Max: 100.0)
...

[MARKET DATA] VIX: 20.50 (Yahoo Finance) | SPX: 6797.00 (Yahoo Finance)

[BOT STARTED] Update interval: 300s
```

### **First Cycle Output:**

```
================================================================================
TRADING CYCLE - 2026-01-24 10:30:00 UTC
================================================================================

[MARKET REGIME] TRANSITIONAL
Action: CAUTIOUS | Message: VIX elevated - Use mean reversion primary

[BENNER CYCLE] Selective Accumulation | Allocation: 50%

[MEAN REVERSION ANALYSIS] 60% allocation
EURUSD: $1.08 | RSI: 35.2
Signal: BUY | Lower BB touch, RSI=35.2, Above 200MA

[DRY-RUN] Would open BUY EURUSD: 0.050 lots @ $1.08000
[DRY-RUN] SL: $1.07500, TP: $1.09000
[DRY-RUN] Strategy: Mean Reversion

[PORTFOLIO SUMMARY]
Exposure: 0.0% (Target: 50%)
Open Positions: 0
```

---

## 📚 **Features Guide**

### **1. Dry-Run Mode (Testing)**

**Purpose:** Test the bot without risking real money

**How to Enable:**
```bash
# In .env file:
DRY_RUN=True
```

**What It Does:**
- ✅ Connects to MT5 and analyzes markets
- ✅ Generates trading signals
- ✅ Logs what trades WOULD be executed
- ❌ Does NOT send real orders
- ❌ Does NOT modify positions

**When to Use:**
- First time running the bot
- Testing new symbols
- Testing configuration changes
- Monitoring strategy performance

### **2. Performance Tracking**

**Files Created:**
- `performance_stats.json` - Complete trade history
- `trade_journal.csv` - Spreadsheet-friendly trade log

**Metrics Tracked:**
- Total trades
- Win rate (%)
- Total profit/loss
- Average win/loss
- Profit factor
- Daily P/L

**View Statistics:**
Check the logs after each cycle:
```
[PERFORMANCE] Trades: 15, Win Rate: 73.3%, Total P/L: $450.25
```

### **3. Telegram Alerts**

**Types of Alerts:**
- 💰 Trade opened (symbol, lots, entry, SL, TP)
- 🟢/🔴 Trade closed (symbol, profit/loss)
- ⚠️ Market warnings (VIX spikes, support breaks)
- ✅ Bot startup/shutdown
- ❌ Errors and crashes

**Example Alert:**
```
✅ SUCCESS

Bot v3.0 started successfully
Account: 5987063
Balance: $10,000.00
DRY RUN: True
```

### **4. Weekend Protection**

**What It Does:**
- Checks if it's Saturday or Sunday
- Checks if it's Friday after 22:00 UTC (market close)
- Skips trading cycles during weekends
- Logs next market open time

**Log Output:**
```
[WEEKEND] Market closed. Next open: 2026-01-27 22:00 UTC
```

### **5. Risk Management**

**Total Exposure Limit:**
- Maximum 30% of account exposed at once
- Prevents opening new trades if limit reached

**Correlation Check:**
- Won't open EURUSD if already have GBPUSD (80% correlated)
- Prevents over-exposure to same market movements

**Position Limits:**
- Max 2% risk per trade
- Proper stop losses (50 pips)
- Trailing stops to lock in profits

### **6. Trailing Stops**

**How It Works:**
- Activates only on winning positions
- Trails 30 pips below current price (long positions)
- Automatically moves stop loss up as profit grows
- Never moves stop loss down (only protects profits)

**Example:**
```
[TRAIL] Updated EURUSD SL from 1.07500 to 1.08200
```

---

## 📊 **Monitoring**

### **Log Files:**

1. **benner_bot_v3.log** - Main log file
   - All bot activity
   - Trading signals
   - Errors and warnings
   - Rotates at 10MB (keeps 5 backups)

2. **trade_journal.csv** - Trade history
   - Timestamp, symbol, action, lots
   - Entry/exit prices
   - Profit/loss
   - Strategy and reason

3. **performance_stats.json** - Statistics
   - Complete trade history
   - Daily P/L breakdown
   - Performance metrics

### **Real-Time Monitoring:**

**Watch logs live:**
```bash
# Linux/Mac:
tail -f benner_bot_v3.log

# Windows PowerShell:
Get-Content benner_bot_v3.log -Wait
```

**Check CSV in Excel:**
- Open `trade_journal.csv` in Excel
- See all your trades
- Create pivot tables for analysis

### **Key Metrics to Watch:**

| Metric | Good | Warning | Action |
|--------|------|---------|--------|
| Win Rate | > 60% | 40-60% | < 40%: Review strategy |
| Exposure | < 30% | 30-40% | > 40%: Stop trading |
| Profit Factor | > 1.5 | 1.0-1.5 | < 1.0: Losing money |
| Open Positions | 1-3 | 4-5 | > 5: Too many |

---

## 🔧 **Troubleshooting**

### **Error: "MT5 initialization failed"**

**Cause:** MT5 not running  
**Fix:**
1. Open MetaTrader 5
2. Make sure it's logged in
3. Try running bot again

---

### **Error: "Configuration errors: MT5_PASSWORD not set"**

**Cause:** `.env` file missing or incomplete  
**Fix:**
1. Check if `.env` file exists (not `.env.template`)
2. Open `.env` and verify all values are filled
3. Make sure no quotes around values

---

### **Warning: "AUTOMATED TRADING IS DISABLED IN MT5!"**

**Cause:** MT5 settings block automated trading  
**Fix:**
1. In MT5: Tools → Options → Expert Advisors
2. Check "Allow automated trading"
3. Click OK
4. Restart MT5
5. Restart bot

---

### **Error: "Symbol EURUSD not found"**

**Cause:** Wrong symbol name for your broker  
**Fix:**
1. In MT5, press Ctrl+U (Market Watch)
2. Right-click → Symbols
3. Find the exact spelling your broker uses
4. Update symbol names in code (line ~40)

---

### **No Trades Being Executed (Not Dry-Run)**

**Possible Causes:**

1. **Market conditions:** No setups meet criteria
   - Check logs for "Signal: HOLD"
   - Wait for better conditions

2. **Risk limits reached:**
   - Check "Cannot open {symbol}: Max exposure reached"
   - Close some positions or wait

3. **Weekend:** Market is closed
   - Check for "[WEEKEND] Market closed"

4. **Filters too strict:**
   - Check RSI threshold settings
   - Review signal generation logs

---

## ❓ **FAQ**

### **Q: Is it safe to run on a live account?**

A: Only after:
1. ✅ Testing on DEMO for 2+ weeks
2. ✅ Verifying positive performance
3. ✅ Understanding all settings
4. ✅ Starting with DRY_RUN=False on DEMO first
5. ✅ Then switching to live with small account

### **Q: How much money do I need?**

A: Minimum $1,000 for proper risk management. The 2% per trade rule means:
- $1,000 account = $20 risk per trade
- $5,000 account = $100 risk per trade
- $10,000 account = $200 risk per trade

### **Q: Can I run multiple bots?**

A: Not recommended on same account. Better to:
- Use one bot per MT5 account
- Or modify MAGIC_NUMBER for each bot instance

### **Q: What happens if my computer restarts?**

A: The bot stops. Open positions remain in MT5. Options:
1. Run bot on VPS (Virtual Private Server)
2. Use a dedicated computer
3. Enable auto-start on boot

### **Q: Can I customize the strategy?**

A: Yes! Edit these in the code:
- `Config.STOP_LOSS_PIPS` (default: 50)
- `Config.TAKE_PROFIT_PIPS` (default: 100)
- `Config.RSI_BUY_THRESHOLD` (default: 40)
- `Config.SYMBOLS` (add/remove trading pairs)

### **Q: How do I stop the bot?**

A: Press `Ctrl+C` in terminal. It will:
1. Stop trading cycles
2. Save performance data
3. Close MT5 connection
4. Keep positions open (they don't auto-close)

### **Q: Where can I get help?**

A: Check:
1. This README
2. Log files (`benner_bot_v3.log`)
3. Code comments
4. Performance stats

---

## 🎯 **Best Practices**

### **✅ DO:**
- Start with DRY_RUN=True
- Test on DEMO account first
- Monitor daily for first week
- Keep log files
- Track performance
- Review trades weekly
- Use Telegram alerts
- Backup `.env` file (securely!)

### **❌ DON'T:**
- Start with live account
- Commit `.env` to git
- Share your credentials
- Run without monitoring
- Ignore warning messages
- Modify code without testing
- Run on unstable internet
- Trade during high-impact news

---

## 📈 **Expected Results (If Benner Cycle is Correct)**

### **January - May 2026:**
- Target: +15-25% from trading
- Method: Mean reversion + momentum
- Risk: Controlled with 2% per trade

### **Mid-2026:**
- Benner predicts market correction
- Bot will reduce exposure (40% → 20%)
- Defensive mode activates

### **Success Criteria:**
- Win rate > 60%
- Profit factor > 1.5
- Drawdown < 15%
- Beating S&P 500

---

## 🔐 **Security Notes**

**NEVER:**
- Commit `.env` file to GitHub/Git
- Share your `.env` file
- Post your credentials online
- Use same password for multiple accounts

**ALWAYS:**
- Keep `.env` file private
- Use strong passwords
- Enable 2FA on MT5 if available
- Review trade journal regularly
- Monitor for unusual activity

---

## 📞 **Support Checklist**

If you need help, provide:
- [ ] Last 50 lines of `benner_bot_v3.log`
- [ ] Your `.env` settings (hide password!)
- [ ] MT5 version and broker name
- [ ] What you expected vs what happened
- [ ] Error messages (full text)

---

## 🎓 **Learning Resources**

### **Understanding the Strategy:**
- Benner Cycle: 150-year market pattern
- Mean Reversion: Buy oversold, sell overbought
- Momentum: Ride established trends
- Risk Management: Never risk more than 2%

### **Recommended Reading:**
- MetaTrader 5 Python documentation
- Pandas for data analysis
- Technical analysis basics
- Risk management principles

---

**Version:** 3.0  
**Last Updated:** January 2026  
**License:** Educational Use  

**⚠️ DISCLAIMER:**  
This is an educational tool. Past performance does not guarantee future results. Trading involves risk of capital loss. Always test thoroughly on demo accounts before live trading.
