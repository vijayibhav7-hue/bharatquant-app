"""
BharatQuant Enterprise Terminal - Auto-Authenticated Direct Dhan Engine
Reads permanent secrets directly from Streamlit configuration.
"""

import sys
import re
import time
from datetime import datetime
import pytz
import requests
import streamlit as st

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

st.set_page_config(
    page_title="भारतक्वांट - धन (Dhan) F&O टर्मिनल",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# AUTO-LOGIN VIA STREAMLIT SECRETS
# ---------------------------------------------------------
st.sidebar.title("⚡ ब्रोकर लाईव्ह API")

# Secrets मधून आपोआप क्रेडेंशियल्स घेणे
if "DHAN_CLIENT_ID" in st.secrets and "DHAN_ACCESS_TOKEN" in st.secrets:
    clean_client_id = re.sub(r'[^\x20-\x7E]', '', str(st.secrets["DHAN_CLIENT_ID"])).strip()
    clean_token = re.sub(r'[^\x20-\x7E]', '', str(st.secrets["DHAN_ACCESS_TOKEN"])).strip()
    st.sidebar.caption("🔑 Secrets मधून क्रेडेंशियल्स आपोआप लोड झाले आहेत.")
else:
    # Secrets नसल्यास मॅन्युअल बॅकअप इनपुट
    st.sidebar.subheader("🔗 DhanHQ थेट कनेक्शन")
    raw_client_id = st.sidebar.text_input("Dhan Client ID:", type="password")
    raw_token = st.sidebar.text_input("Dhan Access Token:", type="password")
    clean_client_id = re.sub(r'[^\x20-\x7E]', '', str(raw_client_id)).strip() if raw_client_id else ""
    clean_token = re.sub(r'[^\x20-\x7E]', '', str(raw_token)).strip() if raw_token else ""

dhan_connected = False
headers = {}

if clean_client_id and clean_token:
    headers = {
        "access-token": clean_token,
        "client-id": clean_client_id,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    try:
        res_auth = requests.get("https://api.dhan.co/fundlimit", headers=headers, timeout=4)
        if res_auth.status_code == 200:
            dhan_connected = True
            st.sidebar.success("✅ Dhan थेट कनेक्ट झाले!")
        else:
            st.sidebar.error("त्रुटी: Client ID किंवा Token अमान्य आहे.")
    except Exception as e:
        st.sidebar.error(f"कनेक्शन त्रुटी: {str(e)}")

st.sidebar.markdown("---")
symbol = st.sidebar.selectbox("इन्स्ट्रुमेंट निवडा", ["NIFTY 50", "BANK NIFTY"], index=0)
step_val = 50 if symbol == "NIFTY 50" else 100
underlying_scrip = 13 if symbol == "NIFTY 50" else 25

# ---------------------------------------------------------
# LIVE OPTION CHAIN DATA
# ---------------------------------------------------------
spot_price = 23873.45 if symbol == "NIFTY 50" else 51200.00
chain_data = {}
data_source = "🟡 मॅन्युअल / ऑफलाइन मोड"

if dhan_connected:
    try:
        chain_payload = {
            "UnderlyingScrip": underlying_scrip,
            "UnderlyingSeg": "IDX_I"
        }
        res_chain = requests.post("https://api.dhan.co/v2/optionchain", json=chain_payload, headers=headers, timeout=4)
        if res_chain.status_code == 200:
            oc_json = res_chain.json().get("data", {})
            spot_price = float(oc_json.get("last_price", spot_price))
            oc_list = oc_json.get("oc", {})
            for strk_str, strk_info in oc_list.items():
                s_price = float(strk_str)
                chain_data[s_price] = {
                    "ce_ltp": float(strk_info.get("ce", {}).get("last_price", 0.0)),
                    "pe_ltp": float(strk_info.get("pe", {}).get("last_price", 0.0))
                }
            data_source = "🟢 DhanHQ Live Option Chain"
    except Exception:
        pass

auto_atm_strike = int(round(spot_price / step_val) * step_val)
strike_selected = st.sidebar.number_input("स्ट्राईक प्राईस", value=auto_atm_strike, step=step_val)
opt_type = st.sidebar.radio("प्रकार", ["CE (कॉल - तेजी)", "PE (पुट - मंदी)"], horizontal=True)
opt_label = "CE" if "CE" in opt_type else "PE"

# चालू खरा भाव मिळवणे
if dhan_connected and strike_selected in chain_data:
    live_premium = chain_data[strike_selected]["ce_ltp"] if opt_label == "CE" else chain_data[strike_selected]["pe_ltp"]
else:
    # बॅकअप भाव
    if strike_selected == 23900:
        live_premium = 108.50 if opt_label == "CE" else 105.35
    elif strike_selected == 23850:
        live_premium = 136.70 if opt_label == "CE" else 83.40
    else:
        live_premium = 108.50

if not dhan_connected:
    live_premium = st.sidebar.number_input("चालू भाव (मॅन्युअल)", value=live_premium, step=0.5, format="%.2f")

auto_refresh = st.sidebar.checkbox("ऑटो-रिफ्रेश (5s)", value=True)

# ---------------------------------------------------------
# AI AGENTS LEVELS
# ---------------------------------------------------------
trigger_buy = round(live_premium * 1.025, 2)
sl = round(trigger_buy * 0.92, 2)
risk = round(trigger_buy - sl, 2)
t1 = round(trigger_buy + (risk * 1.5), 2)
t2 = round(trigger_buy + (risk * 2.0), 2)
t3 = round(trigger_buy + (risk * 3.0), 2)

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)

# ---------------------------------------------------------
# TERMINAL DISPLAY
# ---------------------------------------------------------
st.title("⚡ भारतक्वांट - थेट F&O टर्मिनल")
st.caption(f"डेटा स्त्रोत: **{data_source}** | निफ्टी स्पॉट: **₹{spot_price:,.2f}** | वेळ: **{now_ist.strftime('%I:%M:%S %p IST')}**")

st.markdown(f"""
<div style="background-color: #0f172a; border: 2px solid #3b82f6; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
    <h3 style="color: #94a3b8; margin: 0; font-size: 16px;">🎯 सक्रिय ट्रेड सेटअप:</h3>
    <h1 style="color: #ffffff; margin: 8px 0; font-size: 34px;">
        {symbol} 👉 <span style="color: {'#10b981' if opt_label == 'CE' else '#ef4444'};">{strike_selected} {opt_label}</span> 
        ({'कॉल खरेदी' if opt_label == 'CE' else 'पुट खरेदी'})
    </h1>
    <p style="color: #e2e8f0; margin: 0; font-size: 18px;">
        Dhan वरील चालू खरा भाव (LTP): <b style="color: #38bdf8; font-size: 26px;">₹{live_premium:.2f}</b> | 
        खरेदीची लेव्हल: <b style="color: #fde047; font-size: 24px;">₹{trigger_buy:.2f} च्या वर गेल्यावरच (BUY ABOVE)</b>
    </p>
</div>
""", unsafe_allow_html=True)

# 2x3 GRID CARDS
st.markdown("### 💰 अचूक ट्रेड आकडे (Trade Levels)")

r1c1, r1c2, r1c3 = st.columns(3)
with r1c1:
    st.markdown(f"""
    <div style="background-color: #1e3a8a; padding: 16px; border-radius: 10px; border-left: 6px solid #3b82f6; text-align: center;">
        <p style="color: #93c5fd; margin: 0; font-weight: bold;">प्रवेश लेव्हल (BUY ABOVE)</p>
        <h2 style="color: #ffffff; margin: 4px 0 0 0; font-size: 26px;">₹{trigger_buy:.2f}</h2>
    </div>
    """, unsafe_allow_html=True)
with r1c2:
    st.markdown(f"""
    <div style="background-color: #7f1d1d; padding: 16px; border-radius: 10px; border-left: 6px solid #ef4444; text-align: center;">
        <p style="color: #fca5a5; margin: 0; font-weight: bold;">स्टॉप लॉस (STOP LOSS)</p>
        <h2 style="color: #ffffff; margin: 4px 0 0 0; font-size: 26px;">₹{sl:.2f}</h2>
    </div>
    """, unsafe_allow_html=True)
with r1c3:
    st.markdown(f"""
    <div style="background-color: #064e3b; padding: 16px; border-radius: 10px; border-left: 6px solid #10b981; text-align: center;">
        <p style="color: #6ee7b7; margin: 0; font-weight: bold;">लक्ष्य १ (TARGET 1)</p>
        <h2 style="color: #ffffff; margin: 4px 0 0 0; font-size: 26px;">₹{t1:.2f}</h2>
    </div>
    """, unsafe_allow_html=True)

st.write("")
r2c1, r2c2, r2c3 = st.columns(3)
with r2c1:
    st.markdown(f"""
    <div style="background-color: #064e3b; padding: 16px; border-radius: 10px; border-left: 6px solid #10b981; text-align: center;">
        <p style="color: #6ee7b7; margin: 0; font-weight: bold;">लक्ष्य २ (TARGET 2)</p>
        <h2 style="color: #ffffff; margin: 4px 0 0 0; font-size: 26px;">₹{t2:.2f}</h2>
    </div>
    """, unsafe_allow_html=True)
with r2c2:
    st.markdown(f"""
    <div style="background-color: #064e3b; padding: 16px; border-radius: 10px; border-left: 6px solid #10b981; text-align: center;">
        <p style="color: #6ee7b7; margin: 0; font-weight: bold;">लक्ष्य ३ (TARGET 3)</p>
        <h2 style="color: #ffffff; margin: 4px 0 0 0; font-size: 26px;">₹{t3:.2f}</h2>
    </div>
    """, unsafe_allow_html=True)
with r2c3:
    st.markdown(f"""
    <div style="background-color: #3b0764; padding: 16px; border-radius: 10px; border-left: 6px solid #a855f7; text-align: center;">
        <p style="color: #d8b4fe; margin: 0; font-weight: bold;">रिस्क : रिवॉर्ड (R:R)</p>
        <h2 style="color: #ffffff; margin: 4px 0 0 0; font-size: 26px;">1 : 2.0</h2>
    </div>
    """, unsafe_allow_html=True)

if auto_refresh:
    time.sleep(5)
    st.rerun()
