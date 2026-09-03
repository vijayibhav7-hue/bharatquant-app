"""
BharatQuant Enterprise Terminal - Time-Stamped Intraday Signal Engine
Includes Strict 5-Minute Signal Expiry, Live Time-Tracking & Safety Banners.
"""

import sys
import time
import uuid
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

st.set_page_config(
    page_title="भारतक्वांट - टाइम-स्टँप लाईव्ह ट्रेड्स",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# SIDEBAR SETTINGS
# ---------------------------------------------------------
st.sidebar.title("⚙️ नियंत्रण पॅनल (Settings)")

INSTRUMENTS = {
    "NIFTY 50": {"ticker": "^NSEI", "step": 50},
    "BANK NIFTY": {"ticker": "^NSEBANK", "step": 100},
    "RELIANCE": {"ticker": "RELIANCE.NS", "step": 20},
    "HDFC BANK": {"ticker": "HDFCBANK.NS", "step": 10},
    "TCS": {"ticker": "TCS.NS", "step": 20},
    "INFOSYS": {"ticker": "INFY.NS", "step": 20}
}

selected_name = st.sidebar.selectbox("इन्स्ट्रुमेंट निवडा", list(INSTRUMENTS.keys()), index=0)
inst_config = INSTRUMENTS[selected_name]

auto_refresh = st.sidebar.checkbox("ऑटो-रिफ्रेश (Auto-Refresh 5s)", value=True)
refresh_interval = 5

# ---------------------------------------------------------
# MARKET DATA ENGINE
# ---------------------------------------------------------
@st.cache_data(ttl=5)
def fetch_market_data(ticker):
    try:
        df = yf.download(ticker, period="2d", interval="5m", progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        return df
    except Exception:
        return None

def compute_indicators(df):
    if df is None or len(df) < 15:
        return None
    
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    
    df["Cum_Vol"] = df["Volume"].cumsum()
    df["Cum_Vol_Price"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum()
    df["VWAP"] = df["Cum_Vol_Price"] / (df["Cum_Vol"] + 1e-9)
    
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    
    return df

# ---------------------------------------------------------
# TIME & SIGNAL VALIDATION
# ---------------------------------------------------------
ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)

st.title("⏱️ भारतक्वांट - टाइम-व्हॅलिडेटेड लाईव्ह ट्रेड")
st.caption(f"तुमच्या स्क्रीनवरील सध्याची वेळ: **{now_ist.strftime('%I:%M:%S %p IST')}** (तारीख: {now_ist.strftime('%d-%b-%Y')})")

raw_data = fetch_market_data(inst_config["ticker"])
data = compute_indicators(raw_data)

if data is None or data.empty:
    st.error("⚠️ मार्केट डेटा उपलब्ध नाही. कृपया काही सेकंदांनी पुन्हा प्रयत्न करा.")
else:
    # Get last candle timestamp
    last_candle_time = data.index[-1]
    if last_candle_time.tzinfo is None:
        last_candle_time = pytz.utc.localize(last_candle_time).astimezone(ist)
    else:
        last_candle_time = last_candle_time.astimezone(ist)

    # Calculate Data Age (Minutes passed since signal candle)
    time_diff_seconds = (now_ist - last_candle_time).total_seconds()
    minutes_old = int(time_diff_seconds // 60)
    is_expired = minutes_old >= 10  # If candle is more than 10 mins old, signal is expired

    last = data.iloc[-1]
    curr_price = float(last["Close"])
    prev_close = float(data.iloc[-2]["Close"]) if len(data) > 1 else curr_price
    price_change = curr_price - prev_close
    p_pct = (price_change / prev_close) * 100 if prev_close else 0.0

    rsi = float(last["RSI"]) if not np.isnan(last["RSI"]) else 50.0
    vwap = float(last["VWAP"]) if not np.isnan(last["VWAP"]) else curr_price
    ema20 = float(last["EMA20"]) if not np.isnan(last["EMA20"]) else curr_price
    ema50 = float(last["EMA50"]) if not np.isnan(last["EMA50"]) else curr_price
    atr = float(last["ATR"]) if not np.isnan(last["ATR"]) else (curr_price * 0.005)

    step = inst_config["step"]
    atm_strike = int(round(curr_price / step) * step)

    # Direction Setup
    is_bullish = curr_price >= vwap and ema20 >= ema50
    if is_bullish:
        recommended_trade = f"{atm_strike} CE (कॉल खरेदी)"
        signal_badge = "🟢 BUY CALL"
        trend_name = "तेजी (Bullish)"
        risk = round(atr * 1.5, 2)
        entry_price = round(curr_price, 2)
        stop_loss = round(entry_price - risk, 2)
        target1 = round(entry_price + (risk * 1.5), 2)
        target2 = round(entry_price + (risk * 2.0), 2)
        target3 = round(entry_price + (risk * 3.0), 2)
    else:
        recommended_trade = f"{atm_strike} PE (पुट खरेदी)"
        signal_badge = "🔴 BUY PUT"
        trend_name = "मंदी (Bearish)"
        risk = round(atr * 1.5, 2)
        entry_price = round(curr_price, 2)
        stop_loss = round(entry_price + risk, 2)
        target1 = round(entry_price - (risk * 1.5), 2)
        target2 = round(entry_price - (risk * 2.0), 2)
        target3 = round(entry_price - (risk * 3.0), 2)

    # ---------------------------------------------------------
    # TIME STATUS ALERT BANNER (LIVE vs EXPIRED)
    # ---------------------------------------------------------
    signal_gen_time_str = last_candle_time.strftime("%I:%M:%S %p")
    
    if is_expired:
        st.markdown(f"""
        <div style="background-color: #450a0a; border: 2px solid #ef4444; padding: 18px; border-radius: 12px; margin-bottom: 20px;">
            <h2 style="color: #fca5a5; margin: 0; font-size: 22px;">⛔ जुना ट्रेड / सिग्नल एक्सपायर झाला आहे (EXPIRED)</h2>
            <p style="color: #ffffff; margin: 6px 0 0 0; font-size: 16px;">
                हा संकेत <b>{signal_gen_time_str} IST</b> वाजता आला होता. याला <b>{minutes_old} मिनिटे</b> झाली आहेत. 
                <br>⚠️ <b>दुपारी किंवा उशिरा हा ट्रेड घेऊ नका, तोटा होऊ शकतो.</b> नवीन सिग्नल येण्याची वाट पहा.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background-color: #064e3b; border: 2px solid #10b981; padding: 18px; border-radius: 12px; margin-bottom: 20px;">
            <h2 style="color: #6ee7b7; margin: 0; font-size: 22px;">🟢 हा चालू लाईव्ह ट्रेड आहे (ACTIVE LIVE TRADE)</h2>
            <p style="color: #ffffff; margin: 6px 0 0 0; font-size: 16px;">
                सिग्नल वेळ: <b>{signal_gen_time_str} IST</b> (फक्त <b>{minutes_old} मिनिटांपूर्वी</b> तयार झाला).
                सध्या हा ट्रेड वैध आहे!
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Main Recommendation Display
    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #1e293b, #0f172a); padding: 20px; border-radius: 14px; border: 2px solid #3b82f6; margin-bottom: 20px;">
        <h4 style="color: #94a3b8; margin: 0;">सिग्नल वेळ: {signal_gen_time_str} IST | सध्याची वेळ: {now_ist.strftime('%I:%M:%S %p IST')}</h4>
        <h1 style="color: #ffffff; margin: 8px 0; font-size: 32px;">{selected_name} 👉 <span style="color: {'#10b981' if is_bullish else '#ef4444'};">{recommended_trade}</span></h1>
        <p style="color: #cbd5e1; margin: 0; font-size: 16px;">
            स्पॉट किंमत: <b>₹{curr_price:,.2f}</b> ({price_change:+.2f}%) | 
            स्थिती: <b>{'🟢 ACTIVE' if not is_expired else '🔴 EXPIRED'}</b> | कल: <b>{trend_name}</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # TRADE SETUP 2x3 GRID
    # ---------------------------------------------------------
    st.markdown("### 💰 अचूक ट्रेड आकडे (Entry, Stop Loss & Targets)")

    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.markdown(f"""
        <div style="background-color: #1e3a8a; padding: 18px; border-radius: 12px; border-left: 6px solid #3b82f6; text-align: center;">
            <p style="color: #93c5fd; margin: 0; font-size: 15px; font-weight: bold;">प्रवेश किंमत (ENTRY)</p>
            <h2 style="color: #ffffff; margin: 5px 0 0 0; font-size: 26px;">₹{entry_price:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
    with r1c2:
        st.markdown(f"""
        <div style="background-color: #7f1d1d; padding: 18px; border-radius: 12px; border-left: 6px solid #ef4444; text-align: center;">
            <p style="color: #fca5a5; margin: 0; font-size: 15px; font-weight: bold;">स्टॉप लॉस (STOP LOSS)</p>
            <h2 style="color: #ffffff; margin: 5px 0 0 0; font-size: 26px;">₹{stop_loss:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
    with r1c3:
        st.markdown(f"""
        <div style="background-color: #064e3b; padding: 18px; border-radius: 12px; border-left: 6px solid #10b981; text-align: center;">
            <p style="color: #6ee7b7; margin: 0; font-size: 15px; font-weight: bold;">लक्ष्य १ (TARGET 1)</p>
            <h2 style="color: #ffffff; margin: 5px 0 0 0; font-size: 26px;">₹{target1:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        st.markdown(f"""
        <div style="background-color: #064e3b; padding: 18px; border-radius: 12px; border-left: 6px solid #10b981; text-align: center;">
            <p style="color: #6ee7b7; margin: 0; font-size: 15px; font-weight: bold;">लक्ष्य २ (TARGET 2)</p>
            <h2 style="color: #ffffff; margin: 5px 0 0 0; font-size: 26px;">₹{target2:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
    with r2c2:
        st.markdown(f"""
        <div style="background-color: #064e3b; padding: 18px; border-radius: 12px; border-left: 6px solid #10b981; text-align: center;">
            <p style="color: #6ee7b7; margin: 0; font-size: 15px; font-weight: bold;">लक्ष्य ३ (TARGET 3)</p>
            <h2 style="color: #ffffff; margin: 5px 0 0 0; font-size: 26px;">₹{target3:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
    with r2c3:
        st.markdown(f"""
        <div style="background-color: #3b0764; padding: 18px; border-radius: 12px; border-left: 6px solid #a855f7; text-align: center;">
            <p style="color: #d8b4fe; margin: 0; font-size: 15px; font-weight: bold;">रिस्क : रिवॉर्ड (R:R)</p>
            <h2 style="color: #ffffff; margin: 5px 0 0 0; font-size: 26px;">1 : 2.0</h2>
        </div>
        """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # INTRADAY CHART
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 लाईव्ह कॅन्डलस्टिक चार्ट (5-Minute)")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=data.index, open=data["Open"], high=data["High"], low=data["Low"], close=data["Close"], name="Candles"
    ))
    fig.add_trace(go.Scatter(x=data.index, y=data["EMA20"], name="EMA 20", line=dict(color="#f59e0b", width=1.5)))
    fig.add_trace(go.Scatter(x=data.index, y=data["EMA50"], name="EMA 50", line=dict(color="#3b82f6", width=1.5)))
    fig.add_trace(go.Scatter(x=data.index, y=data["VWAP"], name="VWAP", line=dict(color="#ec4899", width=1.5, dash="dot")))
    fig.update_layout(template="plotly_dark", height=420, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    st.caption("⚠️ **नियम:** सिग्नल आल्यापासून ५ ते १० मिनिटांच्या आतच ट्रेड व्हॅलिड असतो. जुना ट्रेड कधीही एक्झिक्युट करू नका.")

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
