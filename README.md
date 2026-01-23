# MetaTrader5-Samuel-Benner-Hybrid-Trading-Bot

## Complete Setup & Configuration Guide

---

## 📋 TABLE OF CONTENTS
1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [MT5 Configuration](#mt5-configuration)
4. [Bot Configuration](#bot-configuration)
5. [Running the Bot](#running-the-bot)
6. [Strategy Details](#strategy-details)
7. [Risk Management](#risk-management)
8. [Monitoring & Logs](#monitoring--logs)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Customization](#advanced-customization)

---

## 🖥️ SYSTEM REQUIREMENTS

### Minimum Requirements:
- **OS**: Windows 10/11, Linux, or macOS
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum
- **MT5**: MetaTrader 5 terminal installed
- **Internet**: Stable connection

### Recommended:
- **Python**: 3.10+
- **RAM**: 8GB+
- **SSD**: For faster data access

---

## 📦 INSTALLATION

### Step 1: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv mt5_trading_env

# Activate virtual environment
# Windows:
mt5_trading_env\Scripts\activate
# Linux/Mac:
source mt5_trading_env/bin/activate

# Install required packages
pip install MetaTrader5
pip install pandas
pip install numpy
pip install TA-Lib  # Optional: for advanced technical indicators
```

### Step 2: Install MetaTrader 5

1. Download MT5 from your broker's website
2. Install and create a demo or live account
3. Ensure MT5 is running when you start the bot

### Step 3: Download the Trading Bot

Save the main script as `benner_trading_bot.py`

---

## ⚙️ MT5 CONFIGURATION

### Enable Algorithmic Trading:

1. Open MT5 Terminal
2. Go to **Tools → Options → Expert Advisors**
3. Check these boxes:
   - ✅ "Allow algorithmic trading"
   - ✅ "Allow DLL imports"
   - ✅ "Allow WebRequest for listed URL" (if using external data)

### Get Your MT5 Credentials:

You'll need:
- **Login**: Your MT5 account number
- **Password**: Your MT5 password
- **Server**: Your broker's server name (e.g., "ICMarkets-Demo")

To find your server:
1. In MT5, click on your account number at the top
2. The server name is shown in the account details

---

## 🔧 BOT CONFIGURATION

### Edit the Configuration Class:

Open `benner_trading_bot.py` and modify the `Config` class:

```python
class Config:
    # MT5 Connection - CHANGE THESE
    MT5_LOGIN = 12345678          # Your MT5 account number
    MT5_PASSWORD = "YourPassword"  # Your MT5 password
    MT5_SERVER = "YourBroker-Server"  # e.g., "ICMarkets-Demo"
    
    # Trading Symbols - CUSTOMIZE BASED ON YOUR BROKER
    SYMBOLS = {
        'mean_reversion': ['AAPL', 'MSFT', 'GOOGL', 'NVDA'],
        'momentum': ['SPY', 'QQQ', 'IWM', 'DIA'],
        'defensive': ['GLD', 'TLT']
    }
```

### Important Symbol Notes:

**Different brokers use different symbol names:**

| Asset | Broker A | Broker B | Broker C |
|-------|----------|----------|----------|
| Apple | AAPL | AAPL.US | #AAPL |
| S&P 500 ETF | SPY | SPY.US | SPY |
| Euro | EURUSD | EUR/USD | EURUSD |

**How to find YOUR broker's symbol names:**
1. In MT5, press `Ctrl+U` (Market Watch)
2. Right-click → "Symbols"
3. Find the exact spelling your broker uses

### Verify Symbol Availability:

```python
import MetaTrader5 as mt5

mt5.initialize()
mt5.login(YOUR_LOGIN, password="YOUR_PASSWORD", server="YOUR_SERVER")

# Test if symbol exists
symbol = "AAPL"
info = mt5.symbol_info(symbol)
if info is None:
    print(f"{symbol} not found - check symbol name")
else:
    print(f"{symbol} found: {info.description}")
```

---

## 🚀 RUNNING THE BOT

### First Time Setup:

1. **Test Connection First:**

```python
import MetaTrader5 as mt5

# Initialize
if not mt5.initialize():
    print("MT5 initialization failed")
    quit()

# Login
authorized = mt5.login(
    12345678,  # Your login
    password="YourPassword",
    server="YourServer"
)

if authorized:
    print("✅ Connected successfully!")
    print(f"Account balance: ${mt5.account_info().balance}")
else:
    print("❌ Login failed - check credentials")

mt5.shutdown()
```

2. **Run in Demo Mode First:**

```bash
# Always test with DEMO account first!
python benner_trading_bot.py
```

### Normal Operation:

```bash
# Make sure MT5 is running
# Activate your virtual environment
source mt5_trading_env/bin/activate  # Linux/Mac
# or
mt5_trading_env\Scripts\activate  # Windows

# Run the bot
python benner_trading_bot.py
```

### Running as Background Service (Linux):

```bash
# Using screen
screen -S trading_bot
python benner_trading_bot.py
# Press Ctrl+A then D to detach

# To reattach
screen -r trading_bot

# Using nohup
nohup python benner_trading_bot.py > bot.log 2>&1 &
```

### Running as Windows Service:

Use `NSSM` (Non-Sucking Service Manager):

```bash
# Download NSSM from nssm.cc
nssm install BennerTradingBot "C:\Path\To\python.exe" "C:\Path\To\benner_trading_bot.py"
nssm start BennerTradingBot
```

---

## 📊 STRATEGY DETAILS

### Mean Reversion Strategy (60% Allocation)

**Entry Criteria:**
```
✓ Price touches Lower Bollinger Band (20-day, 2 std)
✓ RSI < 30 (strongly oversold) OR RSI < 45 (moderately oversold)
✓ Price above 200-day Moving Average (long-term uptrend)
✓ Volume spike (2x average) - OPTIONAL but increases confidence
```

**Exit Criteria:**
```
→ Primary: Price returns to Middle Bollinger Band (5-8% profit)
→ Aggressive: Price touches Upper Bollinger Band (10-15% profit)
✕ Stop Loss: 3% below entry
```

**Best Targets:**
- Large-cap tech stocks after 8-15% corrections
- Quality names with strong balance sheets
- Stocks in established uptrends

### Momentum Strategy (30% Allocation)

**Entry Criteria:**
```
✓ 20-day MA crosses above 50-day MA (Golden Cross)
✓ Price above both moving averages
✓ VIX < 20 (stable market environment)
✓ Above-average volume on breakout
```

**Exit Criteria:**
```
→ Death Cross: 20-day MA crosses below 50-day MA
→ Trailing stop: 8% below the high
✕ Hard stop: 5% below entry
```

**Best Targets:**
- Small-cap ETFs (Russell 2000)
- Sector rotation plays (Energy, Financials, Industrials)
- Assets with clear uptrends

### Defensive Allocation (10%)

**Hedging Instruments:**
- Inverse ETFs: SPXU, SQQQ (activated when VIX > 20)
- Safe havens: GLD (gold), TLT (long-term treasuries)
- VIX options (if available through your broker)

---

## 🛡️ RISK MANAGEMENT

### Position Sizing Rules:

```python
# Maximum per position: 5% of account
# Formula: Position Size = (Account Balance × 0.05) / Price Risk

# Example with $10,000 account:
Account = $10,000
Entry = $100
Stop Loss = $97
Risk per share = $3

Max Risk = $10,000 × 0.05 = $500
Shares = $500 / $3 = 166 shares
Position Value = 166 × $100 = $16,600

# But total exposure is capped at Benner allocation:
Benner January = 50%
Adjusted Position = $16,600 × 0.50 = $8,300
```

### Benner Cycle Allocation:

| Month | Allocation | Phase | Action |
|-------|-----------|-------|---------|
| Jan 2026 | 50% | Early B | Selective accumulation |
| Feb 2026 | 60% | Early B | Build positions |
| Mar 2026 | 75% | Mid B | Active trading |
| Apr 2026 | 60% | Mid B | Take profits |
| May 2026 | 40% | Late B | Exit mode |
| Jun 2026+ | 20% | Panic A | Defensive only |

### Emergency Exit Triggers:

The bot will **AUTOMATICALLY CLOSE ALL POSITIONS** if:
- ✕ S&P 500 falls below 6,600
- ✕ VIX exceeds 25
- ✕ Account drawdown exceeds 15%

---

## 📝 MONITORING & LOGS

### Log File Location:

All activity is logged to `benner_strategy.log`

### Log Format:

```
2026-01-21 10:30:15 - INFO - TRADING CYCLE - 2026-01-21 10:30:15
2026-01-21 10:30:16 - INFO - Account Balance: $10,000.00
2026-01-21 10:30:17 - INFO - 🎯 MARKET REGIME: TRANSITIONAL
2026-01-21 10:30:18 - WARNING - [WARNING] VIX at 20.99 - Elevated volatility
2026-01-21 10:30:20 - INFO - ✅ BUY MSFT: 0.05 lots @ 425.0 | SL: 412.75 | TP: 440.0
```

### Real-Time Monitoring:

```bash
# Watch logs in real-time (Linux/Mac)
tail -f benner_strategy.log

# Windows PowerShell
Get-Content benner_strategy.log -Wait
```

### Key Metrics to Monitor:

```python
# Portfolio exposure
# Should match Benner allocation
exposure = 47.5%  # Currently at 47.5%, target 50%

# Open positions
# Check for concentration risk
positions = 3  # MSFT, NVDA, IWM

# Win rate
# Track over time
wins = 15 / 20 = 75%  # 15 wins out of 20 trades
```

---

## 🔧 TROUBLESHOOTING

### Common Issues:

#### 1. "MT5 initialization failed"

**Solution:**
- Ensure MT5 terminal is running
- Run as Administrator (Windows)
- Check if MT5 is updated to latest version

#### 2. "Symbol not found"

**Solution:**
```python
# List all available symbols
symbols = mt5.symbols_get()
for s in symbols:
    print(s.name)

# Then update Config.SYMBOLS with correct names
```

#### 3. "Login failed"

**Solution:**
- Verify account number, password, and server name
- Check if account is enabled for trading
- Ensure you're using correct account type (demo vs live)

#### 4. "Order failed" / "Invalid stops"

**Solution:**
```python
# Check symbol specifications
symbol_info = mt5.symbol_info("AAPL")
print(f"Min stop distance: {symbol_info.trade_stops_level} points")
print(f"Min lot: {symbol_info.volume_min}")
print(f"Max lot: {symbol_info.volume_max}")
print(f"Lot step: {symbol_info.volume_step}")
```

#### 5. High CPU usage

**Solution:**
- Increase `UPDATE_INTERVAL` in Config (default: 300s)
- Reduce number of symbols being monitored
- Use higher timeframes (H1 instead of M15)

---

## 🔬 ADVANCED CUSTOMIZATION

### 1. Add Custom Indicators:

```python
# In TechnicalIndicators class
@staticmethod
def stochastic(data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add Stochastic Oscillator"""
    low_min = data['low'].rolling(window=period).min()
    high_max = data['high'].rolling(window=period).max()
    
    data['stoch_k'] = 100 * ((data['close'] - low_min) / (high_max - low_min))
    data['stoch_d'] = data['stoch_k'].rolling(window=3).mean()
    
    return data
```

### 2. Integrate External VIX Data:

```python
import requests

def get_vix_from_api() -> float:
    """Fetch real VIX from external API"""
    try:
        # Example using Alpha Vantage
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=VIX&apikey=YOUR_API_KEY"
        response = requests.get(url)
        data = response.json()
        vix = float(data['Global Quote']['05. price'])
        return vix
    except:
        return 20.0  # Default fallback
```

### 3. Add Email Notifications:

```python
import smtplib
from email.mime.text import MIMEText

def send_alert(subject: str, message: str):
    """Send email alert"""
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = 'bot@yourdomain.com'
    msg['To'] = 'you@yourdomain.com'
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('your_email', 'your_password')
        server.send_message(msg)

# Use in bot:
if regime['regime'] == 'HIGH VOLATILITY':
    send_alert("⚠️ MARKET WARNING", regime['message'])
```

### 4. Backtesting Module:

```python
def backtest_strategy(symbol: str, start_date: str, end_date: str):
    """Run historical backtest"""
    # Fetch historical data
    rates = mt5.copy_rates_range(
        symbol, 
        mt5.TIMEFRAME_D1,
        datetime.strptime(start_date, '%Y-%m-%d'),
        datetime.strptime(end_date, '%Y-%m-%d')
    )
    
    df = pd.DataFrame(rates)
    # Calculate indicators
    df = indicators.bollinger_bands(df)
    df = indicators.rsi(df)
    
    # Simulate trades
    trades = []
    for i in range(200, len(df)):
        signal = signal_generator.mean_reversion_signal(df[:i])
        if signal['signal'] == 'BUY':
            trades.append({
                'entry': df.iloc[i]['close'],
                'exit': signal['take_profit'],
                'profit': (signal['take_profit'] - df.iloc[i]['close']) / df.iloc[i]['close']
            })
    
    # Calculate metrics
    win_rate = len([t for t in trades if t['profit'] > 0]) / len(trades)
    avg_profit = np.mean([t['profit'] for t in trades])
    
    print(f"Backtest Results for {symbol}")
    print(f"Total Trades: {len(trades)}")
    print(f"Win Rate: {win_rate*100:.1f}%")
    print(f"Avg Profit: {avg_profit*100:.2f}%")
```

---

## 📚 RECOMMENDED READING

### Understanding the Benner Cycle:
- Original Benner's Prophecies (1875)
- "Market Cycles: The Key to Maximum Returns" by Jake Bernstein
- Historical analysis of 150-year patterns

### Technical Analysis:
- "Technical Analysis of the Financial Markets" by John Murphy
- "Trading Systems and Methods" by Perry Kaufman

### Risk Management:
- "The New Trading for a Living" by Dr. Alexander Elder
- "Risk Management in Trading" by Grant Hagen

---

## ⚠️ IMPORTANT DISCLAIMERS

### Trading Risks:
- **Past performance does not guarantee future results**
- The Benner Cycle has been accurate historically but is NOT guaranteed
- All trading involves risk of capital loss
- Start with DEMO account before live trading
- Never risk more than you can afford to lose

### Bot Limitations:
- Requires stable internet connection
- Dependent on MT5 terminal being operational
- Cannot predict black swan events
- Market conditions can change rapidly

### Best Practices:
1. ✅ Always test on DEMO first (minimum 1 month)
2. ✅ Start with small position sizes
3. ✅ Monitor daily for first week
4. ✅ Keep logs and track performance
5. ✅ Have manual override capability
6. ✅ Review and adjust monthly

---

## 📞 SUPPORT & UPDATES

### Getting Help:
- Check logs first (`benner_strategy.log`)
- Review troubleshooting section
- Test components individually
- Verify MT5 connection separately

### Performance Tracking:
Create a simple spreadsheet to track:
- Daily P/L
- Number of trades
- Win rate
- Current drawdown
- Exposure vs target

### Monthly Review Checklist:
- [ ] Review all closed trades
- [ ] Calculate actual vs expected performance
- [ ] Verify Benner calendar alignment
- [ ] Adjust symbols if needed
- [ ] Check for any errors in logs
- [ ] Update risk parameters if needed

---

## 🎯 QUICK START CHECKLIST

- [ ] Python 3.8+ installed
- [ ] MT5 installed and account created
- [ ] Dependencies installed (`pip install MetaTrader5 pandas numpy`)
- [ ] Config class updated with MY credentials
- [ ] Symbol names verified for MY broker
- [ ] Tested connection to MT5
- [ ] Run on DEMO account first
- [ ] Logs are being generated
- [ ] Monitored first trading cycle
- [ ] Emergency stop procedure understood

---

## 📈 EXPECTED RESULTS (Benner Scenario)

If the Benner Cycle prediction is correct:

**January - May 2026:**
- Target: +15-25% from selective trading
- Method: Mean reversion captures tech bounces
- Method: Momentum rides small-cap rotation

**Mid-2026:**
- Prediction: Market panic/correction
- Protection: Raised 40-50% cash by May
- Result: Minimal drawdown vs buy-and-hold

**Success Metric:**
- Beat S&P 500 by 10-15% through cycle
- Preserve capital during correction
- Ready to deploy at next "Hard Times (C)" phase

---

**Last Updated:** January 2026  
**Version:** 1.0  
**License:** Educational purposes - Use at own risk
