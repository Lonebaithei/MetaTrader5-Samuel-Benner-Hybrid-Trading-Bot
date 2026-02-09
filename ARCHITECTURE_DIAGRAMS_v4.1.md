# BENNER BOT v4.1 - ARCHITECTURE & FLOW DIAGRAMS

## System Architecture 🏗️

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        BENNER BOT v4.1                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
                ▼                 ▼                 ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │ Config       │  │ Risk Manager │  │ Session      │
        │ Loader       │  │ v4.1 NEW ✨  │  │ Manager      │
        │              │  │              │  │ v4.1 NEW ✨  │
        │ Reads .env   │  │ Tracks:      │  │              │
        │              │  │ - Drawdown   │  │ Controls:    │
        └──────────────┘  │ - Kill Switch│  │ - Sessions   │
              │           │ - Limits     │  │ - Market hrs │
              │           │              │  │ - Liquidity  │
              │           └──────────────┘  └──────────────┘
              │                 │                   │
              └─────────────────┼───────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │ Signal       │  │ Position     │  │ Exit         │
        │ Generator    │  │ Manager      │  │ Manager      │
        │              │  │              │  │              │
        │ Analyzes:    │  │ Opens:       │  │ Monitors:    │
        │ - RSI        │  │ - Positions  │  │ - TP/SL      │
        │ - BB         │  │ - With Checks│  │ - Close      │
        │ - Price      │  │   Applied    │  │   Positions  │
        │              │  │              │  │              │
        └──────────────┘  └──────────────┘  └──────────────┘
              │                 │                   │
              └─────────────────┼───────────────────┘
                                │
                                ▼
                        ┌──────────────┐
                        │ MetaTrader 5 │
                        │ Broker API   │
                        │              │
                        │ Executes:    │
                        │ - Orders     │
                        │ - Queries    │
                        │ - Data       │
                        └──────────────┘
```

---

## Trading Cycle Flow 🔄

```
START TRADING CYCLE
        │
        ▼
   ┌─────────────────────────────┐
   │ 1. Update Risk Tracking     │
   │    (NEW in v4.1)            │
   │                             │
   │ • Get current equity        │
   │ • Calculate drawdown        │
   │ • Check kill switch status  │
   │ • Log alerts                │
   └─────────────────────────────┘
        │
        ▼ Is kill switch active AND
          in PAUSE_TRADING mode?
        │
        ├─ YES ──> SKIP TO END (no trading)
        │
        └─ NO ──> CONTINUE
        │
        ▼
   ┌─────────────────────────────┐
   │ 2. Get Tradeable Symbols    │
   │    (NEW in v4.1)            │
   │                             │
   │ For each configured symbol: │
   │ • Check session times       │
   │ • Check market hours (API)  │
   │ • Check liquidity (spread)  │
   │ • Filter to active only     │
   └─────────────────────────────┘
        │
        ▼
   ┌─────────────────────────────┐
   │ 3. For Each Tradeable Symbol│
   │                             │
   │ Loop through [EURUSD,       │
   │ XAUUSD, BTCUSD, ...]        │
   └─────────────────────────────┘
        │
        ├─> EURUSD
        │   ├─ Check signal
        │   ├─ Analyze RSI, BB
        │   ├─ Generate signal
        │   │
        │   ▼ Check Limits (NEW in v4.1)
        │   ├─ Can open globally?
        │   ├─ Can open for EURUSD?
        │   ├─ Under position limits?
        │   │
        │   ▼ YES -> Open Position
        │   └─ NO -> Skip
        │
        ├─> XAUUSD
        │   └─ (same process)
        │
        └─> BTCUSD
            └─ (same process)
        │
        ▼
   ┌─────────────────────────────┐
   │ 4. Manage Existing Positions│
   │                             │
   │ For open positions:         │
   │ • Check take profit         │
   │ • Check stop loss           │
   │ • Close if conditions met   │
   └─────────────────────────────┘
        │
        ▼
   ┌─────────────────────────────┐
   │ 5. Log Cycle Summary        │
   │    (NEW in v4.1)            │
   │                             │
   │ • Equity status             │
   │ • Drawdown percentage       │
   │ • Position count            │
   │ • Kill switch status        │
   │ • Tradeable symbols         │
   └─────────────────────────────┘
        │
        ▼
   END CYCLE
        │
        └─> Wait UPDATE_INTERVAL seconds
            └─> Loop back to START
```

---

## Risk Management Decision Tree 🌳

```
New Trade Signal Generated
        │
        ▼
   ┌──────────────────────────────────┐
   │ Is Kill Switch ACTIVE?           │
   │ (Drawdown >= limit)              │
   └──────────────────────────────────┘
        │
        ├─ YES (Kill switch ON)
        │  │
        │  ▼
        │  Kill switch mode is:
        │  │
        │  ├─ STOP_OPENING
        │  │  └─> Block new positions ❌
        │  │      But manage existing ones ✓
        │  │
        │  ├─ PAUSE_TRADING
        │  │  └─> Block all trading ❌
        │  │
        │  └─ EMERGENCY_CLOSE
        │     └─> Close all positions ❌
        │
        └─ NO (Kill switch OFF)
           │
           ▼
        ┌──────────────────────────────────┐
        │ Position Count Check             │
        │ (NEW in v4.1)                    │
        │                                  │
        │ Current: 5                       │
        │ Max:     5                       │
        └──────────────────────────────────┘
           │
           ├─ Current >= Max?
           │  │
           │  ├─ YES ──> BLOCKED ❌
           │  │
           │  └─ NO
           │      │
           │      ▼
           │   ┌──────────────────────────────────┐
           │   │ Symbol-Specific Check            │
           │   │ (NEW in v4.1)                    │
           │   │                                  │
           │   │ Symbol: EURUSD                   │
           │   │ Current for symbol: 2            │
           │   │ Max per symbol:     2            │
           │   └──────────────────────────────────┘
           │      │
           │      ├─ Current >= Max?
           │      │  │
           │      │  ├─ YES ──> BLOCKED ❌
           │      │  │
           │      │  └─ NO
           │      │      │
           │      │      ▼
           │      │   ┌──────────────────────────────────┐
           │      │   │ ALL CHECKS PASSED                │
           │      │   │                                  │
           │      │   │ ✅ Kill switch: OFF             │
           │      │   │ ✅ Global limit: OK              │
           │      │   │ ✅ Symbol limit: OK              │
           │      │   │ ✅ Session active: YES           │
           │      │   │ ✅ Liquidity: GOOD              │
           │      │   └──────────────────────────────────┘
           │      │      │
           │      │      ▼
           │      │   OPEN POSITION ✓
           │      │
           │      └─> Update position count
           │
           └─> Log decision for monitoring
```

---

## Session Management Flow 🌍

```
Query: "Can I trade EURUSD?"
        │
        ├─ Is ENABLE_TRADING_SESSIONS = True?
        │  │
        │  ├─ NO ──────────────────> Trade (sessions disabled)
        │  │
        │  └─ YES
        │     │
        │     ▼
        │  ┌────────────────────────────────────┐
        │  │ Check Session Times (from .env)    │
        │  │                                    │
        │  │ Current UTC time: 14:30             │
        │  │                                    │
        │  │ EURUSD in sessions:                │
        │  │ ├─ Asian 22:00-08:00 ❌ (not now) │
        │  │ ├─ Europe 08:00-17:00 ✓ (YES!)    │
        │  │ └─ America 13:00-22:00 ✓ (YES!)   │
        │  └────────────────────────────────────┘
        │     │
        │     └─ At least one session active? YES
        │        │
        │        ▼
        │     ├─ Is ENABLE_AUTO_MARKET_HOURS_DETECTION = True?
        │     │  │
        │     │  ├─ NO ──> Use session times only (EURUSD tradeable)
        │     │  │
        │     │  └─ YES
        │     │     │
        │     │     ▼
        │     │  ┌────────────────────────────────────┐
        │     │  │ Query MT5 API (Broker)             │
        │     │  │                                    │
        │     │  │ symbol_info(EURUSD):               │
        │     │  │ • Visible: True ✓                  │
        │     │  │ • Bid: 1.08950                     │
        │     │  │ • Ask: 1.08952                     │
        │     │  │ • Spread: 2 pips ✓                │
        │     │  │                                    │
        │     │  │ Min spread threshold: 2 pips       │
        │     │  │ Actual spread (2) >= threshold (2) │
        │     │  └────────────────────────────────────┘
        │     │     │
        │     │     ├─ Spread too wide? NO
        │     │     │
        │     │     └─> Market is OPEN with good liquidity ✓
        │     │
        │     └─> Can trade EURUSD! ✓
        │
        └────────────────────────────┐
                                     │
                         Result: TRADEABLE ✓
```

---

## Drawdown Tracking Timeline 📉

```
SESSION START: 9:00 AM
Balance: $10,000
│
├─ 9:30 AM - Trade 1: -$100
│  Current Equity: $9,900
│  Daily Drawdown: 1% (Status: NORMAL ✓)
│  Peak: $10,000
│
├─ 10:00 AM - Trade 2: -$200
│  Current Equity: $9,700
│  Daily Drawdown: 3% (Status: NORMAL ✓)
│  Peak: $10,000
│
├─ 10:30 AM - Trade 3: +$500 (recovery!)
│  Current Equity: $10,200
│  Daily Drawdown: -2% (no drawdown, we're up!)
│  Peak: $10,200 (updated)
│  Intraday DD: 0% (no loss from peak)
│
├─ 11:00 AM - Trade 4: -$1,000 (ouch)
│  Current Equity: $9,200
│  Daily Drawdown: 8% (Status: NORMAL ✓)
│  Peak: $10,200 (unchanged)
│  Intraday DD: 9.8% of peak
│
├─ 11:30 AM - Trade 5: -$800
│  Current Equity: $8,400
│  Daily Drawdown: 16% (Status: ALERT ⚠️)
│  Alert Threshold 1: 75% of limit (22.5%)
│  Peak: $10,200
│  Intraday DD: 17.6% of peak
│
├─ 12:00 PM - Trade 6: -$600
│  Current Equity: $7,800
│  Daily Drawdown: 22% (Status: CRITICAL ⚠️)
│  Alert Threshold 2: 50% of limit (15%)
│  Peak: $10,200
│  Intraday DD: 23.5% of peak
│
├─ 12:30 PM - Trade 7 attempted
│  Current Equity: $7,800
│  Daily Drawdown: 22% (Still under 30%)
│  │
│  ├─ Check: Kill switch active? NO (22% < 30%)
│  ├─ Check: Can open position? YES
│  └─ Result: Position OPENS ✓
│
├─ 1:00 PM - Trade 7 closes: -$500
│  Current Equity: $7,300
│  Daily Drawdown: 27% (Status: CRITICAL ⚠️)
│  Alert Threshold 3: 25% of limit (7.5%)
│  Peak: $10,200
│  Intraday DD: 28.4% of peak
│
├─ 1:30 PM - Trade 8 attempted
│  Current Equity: $7,300
│  Daily Drawdown: 27% (Still under 30%)
│  │
│  ├─ Check: Kill switch active? NO (27% < 30%)
│  ├─ Check: Can open position? YES
│  └─ Result: Position OPENS ✓
│
├─ 2:00 PM - Trade 8 closes: -$400
│  Current Equity: $6,900
│  Daily Drawdown: 31% (AT LIMIT!)
│  │
│  └─ 🛑 KILL SWITCH ACTIVATED 🛑
│      Mode: STOP_OPENING
│      New positions: BLOCKED ❌
│      Existing positions: MANAGED ✓
│
├─ 2:30 PM - Trade 9 attempted
│  Current Equity: $6,900
│  Daily Drawdown: 31% (OVER LIMIT!)
│  │
│  ├─ Check: Kill switch active? YES
│  └─ Result: Position BLOCKED ❌
│
├─ 3:00 PM - Market recovery!
│  Current Equity: $7,500
│  Daily Drawdown: 25% (recovering!)
│  Kill Switch: Still active (auto-reset at midnight)
│
├─ ... (no new positions opened) ...
│
└─ 4:00 PM - EOD (End of Day)
   Final Equity: $7,200
   Daily Drawdown: 28%
   Positions: 1 open (Trade 8)
   Status: Waiting for reset time or position closure


NEXT DAY: 9:00 AM
Daily Drawdown Reset (DRAWDOWN_RESET_TIME=00:00)
│
├─ New Daily Start Equity: $7,200
├─ Kill Switch: RESET (inactive)
├─ Peak Equity Reset: $7,200
└─ New positions: CAN OPEN AGAIN ✓
```

---

## Session Matrix Example 🌍

```
TRADING DAY: Monday 9:00 UTC to Tuesday 8:59 UTC

TIME (UTC)   ASIAN          EUROPE         AMERICA        CRYPTO    TRADEABLE?
             22:00-08:00    08:00-17:00    13:00-22:00   24/7      

00:00-08:00  ✓ OPEN        ✗ Closed       ✗ Closed       ✓ Open    EURUSD(Asia)
             (Start)                                               XAUUSD
                                                                   BTCUSD

08:00-09:00  ✗ Closed      ✓ OPEN        ✗ Closed        ✓ Open    EURUSD(Eur)
             (End)         (Start)                                 XAUUSD
                                                                   GBPUSD
                                                                   BTCUSD

09:00-13:00  ✗ Closed      ✓ OPEN        ✗ Closed        ✓ Open    EURUSD(Eur)
                          (Mid)                                   XAUUSD
                                                                   GBPUSD
                                                                   BTCUSD

13:00-17:00  ✗ Closed      ✓ OPEN        ✓ OPEN          ✓ Open    ALL! (Best)
                          (End)         (Start)                   (Overlap=Most
                          BUSIEST!      BUSIEST!                 Liquidity)

17:00-22:00  ✗ Closed      ✗ Closed      ✓ OPEN          ✓ Open    EURUSD(Amer)
                                        (Mid)                     XAUUSD
                                        BUSIEST!                  BTCUSD

22:00-24:00  ✓ OPEN        ✗ Closed      ✓ OPEN          ✓ Open    EURUSD(Both!)
             (Start)                     (End)                     XAUUSD
                                                                   BTCUSD


LIQUIDITY DURING DIFFERENT HOURS:

00:00-08:00: Asian Session (LOWEST)
├─ Tight spreads: 1-2 pips
├─ Lower volume
└─ Good for: Scalping

08:00-13:00: European Session (HIGH)
├─ Tight spreads: 0.5-1.5 pips
├─ High volume
└─ Good for: Range trading, breakouts

13:00-17:00: OVERLAP (HIGHEST!) ⭐
├─ Tightest spreads: 0.2-1 pip
├─ Massive volume
└─ Best for: All trading, large positions

17:00-22:00: American Session (HIGH)
├─ Tight spreads: 1-2 pips
├─ High volume
└─ Good for: Momentum, breakouts

22:00-00:00: Overlap end (MEDIUM)
├─ Spreads: 1-2 pips
└─ Good for: Scalping
```

---

## Kill Switch Activation States 🛑

```
Normal Trading
┌──────────────────────────────────────────────────────────────┐
│ Drawdown: 0-29%                                              │
│ Status: 🟢 GREEN (Safe to trade)                            │
│ Actions: • Opening positions ✓                              │
│          • Managing positions ✓                             │
│          • Taking profits ✓                                 │
│          • Closing losses ✓                                 │
└──────────────────────────────────────────────────────────────┘
          │ (more losses...)
          ▼

ALERT ZONE
┌──────────────────────────────────────────────────────────────┐
│ Drawdown: 75% of limit = 22.5%                              │
│ Status: 🟡 YELLOW (Caution)                                 │
│ Alerts: ⚠️  Warning logged in system                         │
│ Actions: • Opening positions ✓ (still allowed)             │
│          • But monitor closely!                             │
└──────────────────────────────────────────────────────────────┘
          │ (more losses...)
          ▼

CRITICAL ZONE
┌──────────────────────────────────────────────────────────────┐
│ Drawdown: 50% of limit = 15%                                │
│ Status: 🟠 ORANGE (Critical)                                │
│ Alerts: ⚠️  Critical warning logged                          │
│ Actions: • Opening positions ✓ (still allowed)             │
│          • Strongly consider reducing size                  │
└──────────────────────────────────────────────────────────────┘
          │ (more losses...)
          ▼

AT LIMIT
┌──────────────────────────────────────────────────────────────┐
│ Drawdown: 30% (AT THE LIMIT)                                │
│ Status: 🔴 RED (Kill Switch Activating)                     │
│ Alert:  🛑 KILL SWITCH ACTIVATED                            │
│ Mode:   STOP_OPENING                                        │
│ Actions: • Opening positions ❌ BLOCKED                     │
│          • Managing positions ✓ (allowed)                   │
│          • Taking profits ✓ (allowed)                       │
│          • Closing losses ✓ (allowed)                       │
│                                                              │
│ Benefit: Prevents account spiraling further down            │
│ Wait:    For positions to close OR reset time              │
└──────────────────────────────────────────────────────────────┘
          │ (positions recovering or closing)
          ▼

RECOVERY PHASE
┌──────────────────────────────────────────────────────────────┐
│ Drawdown: 28% (below limit again)                           │
│ Status: 🟠 Still orange but improving                       │
│ Kill Switch: Still ACTIVE (won't reset until reset time)   │
│ Actions: • Opening positions ❌ Still BLOCKED               │
│          • Existing positions managed naturally             │
│          • Waiting for reset time                           │
└──────────────────────────────────────────────────────────────┘
          │ (next reset time arrives)
          ▼

RESET / NEW DAY
┌──────────────────────────────────────────────────────────────┐
│ Drawdown: 0% (reset to new day's balance)                   │
│ Status: 🟢 GREEN again!                                    │
│ Kill Switch: ❌ DEACTIVATED                                 │
│ Actions: • Opening positions ✓ ENABLED                     │
│          • Fresh start with current equity                 │
│          • Previous losses don't carry over                │
└──────────────────────────────────────────────────────────────┘
```

---

## Configuration Impact Matrix 💾

```
Setting                    Impact              Risk
─────────────────────────────────────────────────────
MAX_DAILY_DRAWDOWN=15%     More conservative   Low
MAX_DAILY_DRAWDOWN=30%     Balanced            Medium  
MAX_DAILY_DRAWDOWN=50%     Aggressive          High

MAX_CONCURRENT_POSITIONS=3  Few trades         Concentrated risk
MAX_CONCURRENT_POSITIONS=5  Balanced           Medium diversification
MAX_CONCURRENT_POSITIONS=10 Many trades        Over-leverage risk

MAX_POSITIONS_PER_SYMBOL=1  One per symbol     Low concentration
MAX_POSITIONS_PER_SYMBOL=2  Up to 2 per symbol Medium concentration
MAX_POSITIONS_PER_SYMBOL=4  Up to 4 per symbol High concentration

ENABLE_TRADING_SESSIONS=True  Limits to optimal hours  Less opportunities
ENABLE_TRADING_SESSIONS=False Trade 24/7             More opportunities

CRYPTO_TRADE_WEEKENDS=True   All week trading        More crypto opp
CRYPTO_TRADE_WEEKENDS=False  Weekdays only           Fewer crypto opp

UPDATE_INTERVAL=15 sec       Very frequent checks    More CPU usage
UPDATE_INTERVAL=60 sec       Standard checks         Medium CPU
UPDATE_INTERVAL=300 sec      Less frequent          Might miss signals
```

---

**This architecture ensures:**
✅ Risk is always controlled  
✅ Drawdowns are quantifiable  
✅ Trading only happens in optimal conditions  
✅ Over-leverage is prevented  
✅ Account survival is protected  
