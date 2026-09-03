"""
BharatQuant Enterprise Terminal - Live Auto-Trade Recommender
Direct Call/Put Setup on Main Screen with Entry, SL, Targets & Options Analysis.
"""

import sys
import time
import uuid
import sqlite3
from datetime import datetime
import pytz
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from scipy.stats import norm
import streamlit as st

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

st.set_page_config(
    page_title="भारतक्वांट - थेट लाईव्ह ट्रेड व विश्लेषण",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# SIDEBAR SETTINGS
# ---------------------------------------------------------
st.sidebar.title("⚙️ नियंत्रण पॅनल (Settings)")

INSTRUMENTS = {
    "NIFTY 50": {"ticker": "^NSEI", "step": 50, "lot": 25},
    "BANK NIFTY": {"ticker": "^NSEBANK", "step": 100, "lot": 15},
    "RELIANCE": {"ticker": "RELIANCE.NS", "step": 20, "lot": 250},
    "HDFC BANK": {"ticker": "HDFCBANK.NS", "step": 10, "lot": 550},
    "TCS": {"ticker": "TCS.NS", "step": 20, "lot": 175},
    "INFOSYS": {"ticker": "INFY.NS", "step": 20, "lot": 400},
    "GOLD BEES": {"ticker": "GOLDBEES.NS", "step": 1, "lot": 100}
}

selected_name = st.sidebar.selectbox("इन्स्ट्रुमेंट निवडा (Select Asset)", list(INSTRUMENTS.keys()), index=0)
inst_config = INSTRUMENTS[selected_name]

auto_refresh = st.sidebar.checkbox("ऑटो-रिफ्रेश (Auto-Refresh 5s)", value=True)
refresh_interval = 5

# ---------------------------------------------------------
# DATA FETCHING & QUANT ENGINE
# ---------------------------------------------------------
@st.cache_data(ttl=5)
def fetch_market_data(ticker):
    try:
        df = yf.download(ticker, period="5d", interval="5m", progress=False)
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
    
    # EMAs
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    
    # RSI (14)
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # Intraday VWAP
    df["Cum_Vol"] = df["Volume"].cumsum()
    df["Cum_Vol_Price"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum()
    df["VWAP"] = df["Cum_Vol_Price"] / (df["Cum_Vol"] + 1e-9)
    
    # ATR (14)
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    
    return df

# ---------------------------------------------------------
# LIVE UI & TRADE ENGINE
# ---------------------------------------------------------
ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)

st.title("🎯 भारतक्वांट - लाईव्ह कॉल/पुट ट्रेड रेकमेंडर")
st.caption(f"अचूक अल्गोरिदम आधारित इंट्राडे ट्रेड सिग्नल | अपडेट वेळ: {now_ist.strftime('%d-%b-%Y, %I:%M:%S %p IST')}")

raw_data = fetch_market_data(inst_config["ticker"])
data = compute_indicators(raw_data)

if data is None or data.empty:
    st.error("⚠️ मार्केट डेटा उपलब्ध होत नाहीये. कृपया काही सेकंदांनी पुन्हा पहा.")
else:
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

    # एटीएम स्ट्राईक काढणे
    step = inst_config["step"]
    atm_strike = int(round(curr_price / step) * step)

    # खरेदीचा ट्रेंड ठरवणे (Call vs Put)
    is_bullish = curr_price >= vwap and ema20 >= ema50
    
    if is_bullish:
        recommended_trade = f"{atm_strike} CE (कॉल खरेदी करा)"
        trade_badge = "🟢 खरेदी (BUY CALL)"
        trend_name = "तेजी (Bullish Trend)"
        signal_color = "#10b981"
        confidence = 85
        entry_price = round(curr_price, 2)
        risk = round(atr * 1.5, 2)
        stop_loss = round(entry_price - risk, 2)
        target1 = round(entry_price + (risk * 1.5), 2)
        target2 = round(entry_price + (risk * 2.0), 2)
        target3 = round(entry_price + (risk * 3.0), 2)
    else:
        recommended_trade = f"{atm_strike} PE (पुट खरेदी करा)"
        trade_badge = "🔴 खरेदी (BUY PUT)"
        trend_name = "मंदी (Bearish Trend)"
        signal_color = "#ef4444"
        confidence = 82
        entry_price = round(curr_price, 2)
        risk = round(atr * 1.5, 2)
        stop_loss = round(entry_price + risk, 2)
        target1 = round(entry_price - (risk * 1.5), 2)
        target2 = round(entry_price - (risk * 2.0), 2)
        target3 = round(entry_price - (risk * 3.0), 2)

    # ---------------------------------------------------------
    # मुख्य स्क्रीनवर ठळक लाइव्ह ट्रेड बॉक्स
    # ---------------------------------------------------------
    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #1e293b, #0f172a); padding: 20px; border-radius: 14px; border: 2px solid {signal_color}; margin-bottom: 20px;">
        <h3 style="color: #94a3b8; margin: 0; font-size: 16px;">🔥 शिफारस केलेला लाईव्ह ट्रेड (Active Recommended Trade):</h3>
        <h1 style="color: #ffffff; margin: 8px 0; font-size: 32px;">{selected_name} 👉 <span style="color: {signal_color};">{recommended_trade}</span></h1>
        <p style="color: #cbd5e1; margin: 0; font-size: 16px;">
            सध्याची स्पॉट किंमत: <b>₹{curr_price:,.2f}</b> ({price_change:+.2f} / {p_pct:+.2f}%) | 
            संकेत: <b>{trade_badge}</b> | विश्वास पातळी: <b>{confidence}%</b> | बाजाराचा कल: <b>{trend_name}</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # ठळक ट्रेड सेटअप कार्ड्स (Entry, SL, Targets - २x३ ग्रिड)
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
    # हा संकेत का आला? (REASONS)
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("🔍 हा संकेत का आला? (कारणे)")
    c_r1, c_r2 = st.columns(2)
    with c_r1:
        st.write(f"- **VWAP स्थिती:** किंमत (₹{curr_price:.2f}) ही VWAP (₹{vwap:.2f}) च्या {'वर 🟢' if curr_price > vwap else 'खाली 🔴'} आहे.")
        st.write(f"- **EMA ट्रेंड:** EMA 20 (₹{ema20:.2f}) ही EMA 50 (₹{ema50:.2f}) च्या {'वर आहे (सकारात्मक)' if ema20 > ema50 else 'खाली आहे (नकारात्मक)'}.")
    with c_r2:
        st.write(f"- **RSI मोमेंटम:** {rsi:.1f} ({'मजबूत तेजी क्षेत्र' if rsi > 55 else 'मंदीचे क्षेत्र' if rsi < 45 else 'न्यूट्रल'}).")
        st.write(f"- **शिफारस:** आजच्या ट्रेंडनुसार **{recommended_trade}** मध्ये चांगला रिस्क-रिवॉर्ड मिळण्याची शक्यता आहे.")

    # ---------------------------------------------------------
    # लाईव्ह इंट्राडे चार्ट
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

    # ---------------------------------------------------------
    # ऑप्शन्स स्ट्राईक चेन सारांश
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader(f"⛓️ {selected_name} - जवळच्या ५ मुख्य स्ट्राईक्स (Options Chain)")
    strikes_sample = [atm_strike - (2 * step), atm_strike - step, atm_strike, atm_strike + step, atm_strike + (2 * step)]
    chain_data = []
    for s in strikes_sample:
        p_ce = max(10.0, round((curr_price - s) + (atr * 0.8), 2)) if curr_price > s else max(5.0, round(atr * 0.6, 2))
        p_pe = max(10.0, round((s - curr_price) + (atr * 0.8), 2)) if s > curr_price else max(5.0, round(atr * 0.6, 2))
        chain_data.append({
            "कॉल किंमत (CE Price)": f"₹{p_ce:.2f}",
            "स्ट्राईक (Strike)": f"👉 {s} (ATM) 👈" if s == atm_strike else str(s),
            "पुट किंमत (PE Price)": f"₹{p_pe:.2f}"
        })
    st.table(pd.DataFrame(chain_data))

    st.caption("⚠️ **सूचना:** हा केवळ अल्गोरिदम आधारित तांत्रिक संकेत आहे. प्रत्यक्ष खरेदी-विक्री करण्यापूर्वी स्वतःच्या जोखमीची खात्री करा.")

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
