"""
BharatQuant Enterprise Terminal - Single File Production Architecture
Bilingual (मराठी/English), High-Contrast UI, Auto-Refresh, Strict Decoupling.
"""

import os
import sys
import time
import uuid
import sqlite3
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from scipy.stats import norm
import streamlit as st

# Force UTF-8 Output for Windows Terminals
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------
# 1. STREAMLIT CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="भारतक्वांट - अल्गो टर्मिनल",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. BILINGUAL TRANSLATION DICTIONARY
# ---------------------------------------------------------
TRANSLATIONS = {
    "मराठी": {
        "title": "📈 भारतक्वांट एंटरप्राइज टर्मिनल",
        "subtitle": "अल्गोरिदम आधारित भारतीय शेअर बाजार विश्लेषण व ट्रेडिंग प्रणाली",
        "live_price": "लाईव्ह किंमत",
        "signal": "ट्रेडिंग संकेत",
        "buy": "🟢 खरेदी (BUY)",
        "sell": "🔴 विक्री (SELL)",
        "wait": "🟡 प्रतीक्षा करा (WAIT)",
        "entry": "प्रवेश किंमत",
        "stop_loss": "स्टॉप लॉस",
        "target_1": "लक्ष्य १",
        "target_2": "लक्ष्य २",
        "target_3": "लक्ष्य ३",
        "confidence": "विश्वास पातळी",
        "reason": "हा संकेत का आला?",
        "trend": "बाजाराचा कल",
        "bullish": "तेजी (Bullish)",
        "bearish": "मंदी (Bearish)",
        "sideways": "दिशाहीन (Sideways)",
        "data_status": "डेटा स्थिती",
        "delayed": "डेटा काही सेकंद विस्कळीत (Delayed)",
        "disclaimer_title": "⚠️ महत्त्वाची सूचना",
        "disclaimer_text": "हा केवळ शैक्षणिक आणि विश्लेषणात्मक संकेत आहे. थेट ट्रेड करण्यापूर्वी स्वतःची खात्री करा.",
        "market_closed": "बाजार सध्या बंद आहे",
        "market_open": "बाजार चालू आहे",
        "order_exec_title": "सुरक्षित ऑर्डर एक्झिक्युशन",
        "not_sent": "कोणतीही खरी ऑर्डर ब्रोकरकडे पाठवलेली नाही (Analysis Only)"
    },
    "English": {
        "title": "📈 BharatQuant Enterprise Terminal",
        "subtitle": "Algorithmic Indian Stock Market Analysis & Execution System",
        "live_price": "Live Price",
        "signal": "Trade Signal",
        "buy": "🟢 BUY",
        "sell": "🔴 SELL",
        "wait": "🟡 WAIT",
        "entry": "Entry Price",
        "stop_loss": "Stop Loss",
        "target_1": "Target 1",
        "target_2": "Target 2",
        "target_3": "Target 3",
        "confidence": "Confidence",
        "reason": "Why This Signal?",
        "trend": "Market Trend",
        "bullish": "Bullish",
        "bearish": "Bearish",
        "sideways": "Sideways",
        "data_status": "Data Status",
        "delayed": "Data Delayed (Free Source)",
        "disclaimer_title": "⚠️ Disclaimer",
        "disclaimer_text": "This is purely analytical for education. Verify with broker before placing real trades.",
        "market_closed": "Market Closed",
        "market_open": "Market Open",
        "order_exec_title": "Order Execution Safety Gate",
        "not_sent": "No real order has been sent to broker (Analysis Only)"
    }
}

# ---------------------------------------------------------
# 3. SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.title("⚙️ सेटिंग्ज (Settings)")

lang = st.sidebar.selectbox("भाषा निवडा / Select Language", ["मराठी", "English"], index=0)
t = TRANSLATIONS[lang]

# Instruments Mapping
INSTRUMENTS = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "RELIANCE": "RELIANCE.NS",
    "HDFC BANK": "HDFCBANK.NS",
    "TCS": "TCS.NS",
    "INFOSYS": "INFY.NS",
    "GOLD BEES": "GOLDBEES.NS"
}

selected_name = st.sidebar.selectbox("इन्स्ट्रुमेंट निवडा (Select Instrument)", list(INSTRUMENTS.keys()), index=0)
ticker_symbol = INSTRUMENTS[selected_name]

option_type = st.sidebar.radio("ऑप्शन प्रकार (Option Type)", ["CE (कॉल)", "PE (पुट)"], horizontal=True)
opt_suffix = "CE" if "CE" in option_type else "PE"

auto_refresh = st.sidebar.checkbox("ऑटो-रिफ्रेश सुरू ठेवा (Auto-Refresh 5s)", value=True)
refresh_interval = 5

# ---------------------------------------------------------
# 4. MARKET DATA & CALCULATION ENGINE
# ---------------------------------------------------------
@st.cache_data(ttl=5)
def fetch_market_data(ticker):
    try:
        data = yf.download(ticker, period="5d", interval="5m", progress=False)
        if data.empty:
            return None
        # Handle multi-level columns if returned by yfinance
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
        return data
    except Exception:
        return None

def compute_indicators(df):
    if df is None or len(df) < 15:
        return None
    
    # 20 & 50 EMA
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    
    # RSI (14)
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # Intraday VWAP
    df["Cum_Vol"] = df["Volume"].cumsum()
    df["Cum_Vol_Price"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum()
    df["VWAP"] = df["Cum_Vol_Price"] / (df["Cum_Vol"] + 1e-9)
    
    # ATR for Stop Loss calculation
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df["ATR"] = true_range.rolling(14).mean()
    
    return df

# ---------------------------------------------------------
# 5. EXECUTION & SIGNAL LOGIC
# ---------------------------------------------------------
ist = pytz.timezone("Asia/Kolkata")
current_ist = datetime.now(ist)

st.title(t["title"])
st.caption(f"{t['subtitle']} | वेळेचा शिक्का: {current_ist.strftime('%d-%b-%Y, %I:%M:%S %p IST')}")

raw_data = fetch_market_data(ticker_symbol)
data = compute_indicators(raw_data)

if data is None or data.empty:
    st.error("⚠️ डेटा उपलब्ध होत नाहीये. कृपया काही सेकंदांनी पुन्हा पहा.")
else:
    last_row = data.iloc[-1]
    curr_price = float(last_row["Close"])
    prev_close = float(data.iloc[-2]["Close"]) if len(data) > 1 else curr_price
    price_change = curr_price - prev_close
    p_pct = (price_change / prev_close) * 100 if prev_close else 0

    rsi_val = float(last_row["RSI"]) if not np.isnan(last_row["RSI"]) else 50.0
    ema20 = float(last_row["EMA20"]) if not np.isnan(last_row["EMA20"]) else curr_price
    ema50 = float(last_row["EMA50"]) if not np.isnan(last_row["EMA50"]) else curr_price
    vwap_val = float(last_row["VWAP"]) if not np.isnan(last_row["VWAP"]) else curr_price
    atr_val = float(last_row["ATR"]) if not np.isnan(last_row["ATR"]) else (curr_price * 0.005)

    # Determine Trend & Signal
    is_bullish = curr_price > vwap_val and ema20 > ema50 and rsi_val > 50
    is_bearish = curr_price < vwap_val and ema20 < ema50 and rsi_val < 50

    if is_bullish:
        trend_text = t["bullish"]
        trend_color = "#10b981"
        action_signal = t["buy"] if opt_suffix == "CE" else t["wait"]
        confidence = 85 if opt_suffix == "CE" else 40
    elif is_bearish:
        trend_text = t["bearish"]
        trend_color = "#ef4444"
        action_signal = t["buy"] if opt_suffix == "PE" else t["wait"]
        confidence = 82 if opt_suffix == "PE" else 42
    else:
        trend_text = t["sideways"]
        trend_color = "#f59e0b"
        action_signal = t["wait"]
        confidence = 50

    # Risk & Targets (1:1.5, 1:2, 1:3 RR)
    risk_unit = round(atr_val * 1.5, 2)
    entry_price = round(curr_price, 2)
    
    if action_signal == t["buy"]:
        stop_loss = round(entry_price - risk_unit, 2)
        target1 = round(entry_price + (risk_unit * 1.5), 2)
        target2 = round(entry_price + (risk_unit * 2.0), 2)
        target3 = round(entry_price + (risk_unit * 3.0), 2)
    else:
        stop_loss = round(entry_price + risk_unit, 2)
        target1 = round(entry_price - (risk_unit * 1.5), 2)
        target2 = round(entry_price - (risk_unit * 2.0), 2)
        target3 = round(entry_price - (risk_unit * 3.0), 2)

    # ---------------------------------------------------------
    # 6. MODERN DUAL-ROW CARD UI (NO TRUNCATION)
    # ---------------------------------------------------------
    st.markdown("---")
    
    # Top 4 Status Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(f"{selected_name} {t['live_price']}", f"₹{curr_price:,.2f}", f"{price_change:+.2f} ({p_pct:+.2f}%)")
    with m2:
        st.metric(t["signal"], action_signal)
    with m3:
        st.metric(t["confidence"], f"{confidence}%")
    with m4:
        st.metric(t["trend"], trend_text)

    st.markdown("### 💰 ट्रेड सेटअप (Trade Setup)")

    # 2x3 Grid with High-Contrast Colors
    row1_col1, row1_col2, row1_col3 = st.columns(3)
    with row1_col1:
        st.markdown(f"""
        <div style="background-color: #1e3a8a; padding: 18px; border-radius: 12px; border-left: 6px solid #3b82f6; text-align: center;">
            <p style="color: #93c5fd; margin: 0; font-size: 15px; font-weight: bold;">{t['entry']}</p>
            <h2 style="color: #ffffff; margin: 5px 0 0 0; font-size: 26px;">₹{entry_price:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with row1_col2:
        st.markdown(f"""
        <div style="background-color: #7f1d1d; padding: 18px; border-radius: 12px; border-left: 6px solid #ef4444; text-align: center;">
            <p style="color: #fca5a5; margin: 0; font-size: 15px; font-weight: bold;">{t['stop_loss']}</p>
            <h2 style="color: #ffffff; margin: 5px 0 0 0; font-size: 26px;">₹{stop_loss:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with row1_col3:
        st.markdown(f"""
        <div style="background-color: #064e3b; padding: 18px; border-radius: 12px; border-left: 6px solid #10b981; text-align: center;">
            <p style="color: #6ee7b7; margin: 0; font-size: 15px; font-weight: bold;">{t['target_1']}</p>
            <h2 style="color: #ffffff; margin: 5px 0 0 0; font-size: 26px;">₹{target1:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.write("") # Spacer
    row2_col1, row2_col2, row2_col3 = st.columns(3)
    with row2_col1:
        st.markdown(f"""
        <div style="background-color: #064e3b; padding: 18px; border-radius: 12px; border-left: 6px solid #10b981; text-align: center;">
            <p style="color: #6ee7b7; margin: 0; font-size: 15px; font-weight: bold;">{t['target_2']}</p>
            <h2 style="color: #ffffff; margin: 5px 0 0 0; font-size: 26px;">₹{target2:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with row2_col2:
        st.markdown(f"""
        <div style="background-color: #064e3b; padding: 18px; border-radius: 12px; border-left: 6px solid #10b981; text-align: center;">
            <p style="color: #6ee7b7; margin: 0; font-size: 15px; font-weight: bold;">{t['target_3']}</p>
            <h2 style="color: #ffffff; margin: 5px 0 0 0; font-size: 26px;">₹{target3:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with row2_col3:
        st.markdown(f"""
        <div style="background-color: #3b0764; padding: 18px; border-radius: 12px; border-left: 6px solid #a855f7; text-align: center;">
            <p style="color: #d8b4fe; margin: 0; font-size: 15px; font-weight: bold;">रिस्क : रिवॉर्ड (R:R)</p>
            <h2 style="color: #ffffff; margin: 5px 0 0 0; font-size: 26px;">1 : 2.0</h2>
        </div>
        """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 7. EXPLANATION BULLETS (REASONING)
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader(f"🔍 {t['reason']}")
    
    reasons = []
    if curr_price > vwap_val:
        reasons.append("✓ किंमत VWAP पातळीच्या वर आहे (तेजीचा जोर).")
    else:
        reasons.append("✓ किंमत VWAP पातळीच्या खाली आहे (मंदीचा प्रभाव).")
        
    if ema20 > ema50:
        reasons.append("✓ EMA 20 हा EMA 50 च्या वर आहे (अल्पकालीन ट्रेंड सकारात्मक).")
    else:
        reasons.append("✓ EMA 20 हा EMA 50 च्या खाली आहे (अल्पकालीन ट्रेंड नकारात्मक).")
        
    if 45 <= rsi_val <= 65:
        reasons.append(f"✓ RSI {rsi_val:.1f} वर स्थिर आहे (ओव्हरबॉट्स नाही, योग्य गती).")
    elif rsi_val > 65:
        reasons.append(f"⚠️ RSI {rsi_val:.1f} उच्च पातळीवर आहे (Pullback चा धोका असू शकतो).")
    else:
        reasons.append(f"✓ RSI {rsi_val:.1f} मंदीच्या झोनमध्ये आहे.")

    for r in reasons:
        st.markdown(f"- **{r}**")

    # ---------------------------------------------------------
    # 8. TECHNICAL CANDLESTICK CHART
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 लाईव्ह चार्ट (5-Minute Intraday Candlestick)")
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data["Open"], high=data["High"],
        low=data["Low"], close=data["Close"],
        name="Price"
    ))
    fig.add_trace(go.Scatter(x=data.index, y=data["EMA20"], name="EMA 20", line=dict(color="#f59e0b", width=1.5)))
    fig.add_trace(go.Scatter(x=data.index, y=data["EMA50"], name="EMA 50", line=dict(color="#3b82f6", width=1.5)))
    fig.add_trace(go.Scatter(x=data.index, y=data["VWAP"], name="VWAP", line=dict(color="#ec4899", width=1.5, dash="dot")))
    
    fig.update_layout(
        template="plotly_dark",
        height=450,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # 9. SAFETY GATE & DISCLAIMER
    # ---------------------------------------------------------
    st.info(f"🛡️ **{t['order_exec_title']}**: {t['not_sent']}")
    st.warning(f"{t['disclaimer_title']}: {t['disclaimer_text']}")

# ---------------------------------------------------------
# 10. IN-BUILT SLEEP AUTO-REFRESH (NO EXTERNAL LIB NEEDED)
# ---------------------------------------------------------
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
