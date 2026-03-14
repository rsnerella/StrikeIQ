# Upstox WebSocket Subscription Modes - Complete Testing Guide

## 🎯 **Current Status: full_d30 Mode Active**

**Current Configuration:**
```python
"mode": "full_d30"  # Use full_d30 mode for complete options data with bid/ask/greeks
```

**Current Results:**
- ✅ **Index instruments**: MarketFF with complete data
- ❌ **Options instruments**: IndexFF with limited data (LTP + CP only)

## 📊 **All Available Subscription Modes**

### **1. ltp Mode**
```python
"mode": "ltp"
```
**Expected Data:**
- ✅ LTP: YES
- ❌ Bid/Ask: NO
- ❌ Greeks: NO
- ❌ OI: NO
- ❌ Volume: NO

**Use Case:** Fastest updates, minimal bandwidth

### **2. option_greek Mode**
```python
"mode": "option_greek"
```
**Expected Data:**
- ❌ LTP: NO
- ❌ Bid/Ask: NO
- ✅ Greeks: YES (delta, theta, gamma, vega, rho)
- ❌ OI: NO
- ❌ Volume: NO

**Use Case:** Options Greeks analysis only

### **3. full Mode**
```python
"mode": "full"
```
**Expected Data:**
- ✅ LTP: YES
- 🤔 Bid/Ask: LIMITED
- 🤔 Greeks: LIMITED
- 🤔 OI: LIMITED
- 🤔 Volume: LIMITED

**Use Case:** Basic full data, may have limited options data

### **4. full_d30 Mode (Current)**
```python
"mode": "full_d30"
```
**Expected Data:**
- ✅ LTP: YES
- ✅ Bid/Ask: YES (30 levels)
- ✅ Greeks: YES (all Greeks)
- ✅ OI: YES (real-time)
- ✅ Volume: YES (real-time)

**Use Case:** Complete market depth with 30 levels

### **5. full_d5 Mode**
```python
"mode": "full_d5"
```
**Expected Data:**
- ✅ LTP: YES
- ✅ Bid/Ask: YES (5 levels)
- ✅ Greeks: YES (all Greeks)
- ✅ OI: YES (real-time)
- ✅ Volume: YES (real-time)

**Use Case:** Faster than d30, still complete data

### **6. full_d10 Mode**
```python
"mode": "full_d10"
```
**Expected Data:**
- ✅ LTP: YES
- ✅ Bid/Ask: YES (10 levels)
- ✅ Greeks: YES (all Greeks)
- ✅ OI: YES (real-time)
- ✅ Volume: YES (real-time)

**Use Case:** Good balance of depth and performance

## 🧪 **How to Test Each Mode**

### **Method 1: Manual Edit**
1. Open `backend/app/services/websocket_market_feed.py`
2. Find line 863: `"mode": "full_d30"`
3. Change to desired mode: `"mode": "full_d10"`
4. Restart the system
5. Monitor logs for data completeness

### **Method 2: Use Mode Switcher**
```bash
# Test full_d10 mode
python switch_mode.py 6

# Test full_d5 mode  
python switch_mode.py 5

# Test option_greek mode
python switch_mode.py 2

# Test ltp mode
python switch_mode.py 1
```

## 📋 **What to Monitor in Logs**

### **For Complete Data (MarketFF):**
```
🔍 OPTION MESSAGE ANALYSIS - NSE_FO|57724: ff_type=marketFF
✅ MARKETFF DETECTED - Complete data available - Processing now!
🎉 SUCCESS! OPTION INSTRUMENT NSE_FO|57724 RECEIVED AS MARKETFF
DEBUG MARKET BID/ASK: bid=340.0, ask=341.0, bid_qty=1000, ask_qty=500
DEBUG MARKET GREEKS: iv=0.25, delta=0.45, theta=-0.05, gamma=0.08, vega=0.12
DEBUG MARKET DETAILS: oi=2161965, oi_change=1000, volume=65886340
```

### **For Limited Data (IndexFF):**
```
🔍 OPTION MESSAGE ANALYSIS - NSE_FO|57724: ff_type=indexFF
⚠️ INDEXFF DETECTED - Limited data only - Skipping
⚠️ SKIPPING INDEXFF FOR OPTION NSE_FO|57724 - Waiting for MarketFF data
```

## 🎯 **Recommended Testing Sequence**

### **Step 1: Test full_d10 Mode**
```bash
python switch_mode.py 6
# Restart system and monitor for MarketFF messages
```

### **Step 2: Test full_d5 Mode**
```bash
python switch_mode.py 5
# Restart system and monitor for MarketFF messages
```

### **Step 3: Test option_greek Mode**
```bash
python switch_mode.py 2
# Restart system and monitor for Greeks data
```

### **Step 4: Test full Mode**
```bash
python switch_mode.py 3
# Restart system and monitor for any improvements
```

### **Step 5: Test ltp Mode**
```bash
python switch_mode.py 1
# Restart system and verify LTP-only behavior
```

## 🔍 **Expected Results by Mode**

### **If MarketFF Messages Appear:**
- ✅ **Complete data extraction working**
- ✅ **Bid/Ask prices available**
- ✅ **Greeks data available**
- ✅ **OI/Volume data available**

### **If Still IndexFF Only:**
- ❌ **Upstox doesn't send MarketFF for options**
- ❌ **All modes will have same limitation**
- ✅ **Current IndexFF extraction is optimal**

## 🎉 **Success Criteria**

### **Complete Success:**
```
✅ MarketFF messages for options
✅ Real-time bid/ask data
✅ Complete Greeks data
✅ Real-time OI/Volume data
✅ Full WebSocket operation
```

### **Partial Success (Current):**
```
✅ Real-time LTP data
✅ Change price data
✅ Complete index data
✅ 100% WebSocket operation
❌ Limited options data (Upstox limitation)
```

## 🚀 **Next Steps**

1. **Test full_d10 and full_d5 modes first** (highest probability)
2. **Monitor logs for MarketFF messages**
3. **If still IndexFF only, accept current limitation**
4. **Consider hybrid approach** (WebSocket + REST API)
5. **Focus on optimizing current WebSocket data**

**The system is working correctly - we just need to find if any mode provides complete options data from Upstox!**
