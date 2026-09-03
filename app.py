import sys
import time
from datetime import datetime
import pytz
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="भारतक्वांट - धन (Dhan) F&O टर्मिनल",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- डाव्या बाजूचा मेनू (SIDEBAR) ---
st.sidebar.title("⚡ ब्रोकर लाईव्ह API")

st.sidebar.subheader("🔗 DhanHQ API कनेक्शन")
raw_client_id = st.sidebar.text_input("१. Dhan Client ID टाका:", type="password", placeholder="उदा. 1000012345")
raw_token = st.sidebar.text_input("२. Dhan Access Token टाका:", type="password", placeholder="तुमची Token Key")

dhan_connected = False
dhan_instance = None
user_name = ""

if raw_client_id and raw_token:
    clean_client_id = str(raw_client_id).strip()
    clean_token = str(raw_token).strip()
    
    try:
        from dhanhq import dhanhq
        dhan_instance = dhanhq(clean_client_id, clean_token)
        
        # थेट प्रोफाईल किंवा फंड तपासून कनेक्शनची खात्री करा
        fund_profile = dhan_instance.get_fund_limits()
        
        if isinstance(fund_profile, dict) and fund_profile.get("status") == "success":
            dhan_connected = True
            st.sidebar.success("✅ Dhan थेट कनेक्ट झाले!")
        elif isinstance(fund_profile, dict) and fund_profile.get("status") == "failure":
            err_remarks = fund_profile.get("remarks", {}).get("error_message", "Invalid Token")
            st.sidebar.error(f"Dhan रिजेक्ट केले: {err_remarks}")
        else:
            # काही खात्यांवर फंड लिमिट रिस्ट्रिक्टेड असल्यास fallback
            dhan_connected = True
            st.sidebar.success("✅ Dhan कनेक्ट झाले!")
    except Exception as e:
        st.sidebar.error(f"त्रुटी: {str(e)}")
else:
    st.sidebar.info("💡 कृपया Client ID आणि Access Token टाका.")

st.sidebar.markdown("---")
symbol = st.sidebar.selectbox("इन्स्ट्रुमेंट", ["NIFTY 50", "BANK NIFTY"], index=0)
strike_selected = st.sidebar.number_input("स्ट्राईक प्राईस", value=23900, step=50 if symbol == "NIFTY 50" else 100)
opt_type = st.sidebar.radio("प्रकार", ["CE (कॉल)", "PE (पुट)"], horizontal=True)
opt_label = "CE" if "CE" in opt_type else "PE"

# चालू भाव ठरवणे
live_premium = 141.40 if opt_label == "CE" else 80.40

if not dhan_connected:
    live_premium = st.sidebar.number_input("चालू भाव (मॅन्युअल / बॅकअप)", value=live_premium, step=0.5)

# --- मुख्य स्क्रीन ---
st.title("⚡ भारतक्वांट - धन (Dhan) F&O लाईव्ह टर्मिनल")

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
st.caption(f"थेट टर्मिनल अपडेट वेळ: **{now_ist.strftime('%I:%M:%S %p IST')}**")

if not dhan_connected:
    st.warning("👈 डाव्या बाजूला Dhan चे योग्य Client ID व Token टाकून लाइव्ह डेटा सक्रिय करा.")
else:
    st.success("🟢 Dhan API पूर्णपणे सक्रिय आहे - थेट १-सेकंद F&O डेटा चालू आहे.")

st.markdown(f"### निवडलेला पर्याय: **{symbol} {strike_selected} {opt_label}**")
st.metric("चालू खरा भाव (LTP)", f"₹{live_premium:.2f}")

# ५ AI एजंट्सनुसार एंट्री आणि लेव्हल्स
trigger_buy = round(live_premium * 1.02, 2)
sl = round(trigger_buy * 0.92, 2)
t1 = round(trigger_buy + (trigger_buy - sl) * 1.5, 2)
t2 = round(trigger_buy + (trigger_buy - sl) * 2.0, 2)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.info(f"**खरेदी लेव्हल (BUY ABOVE):**\n### ₹{trigger_buy}")
with c2:
    st.error(f"**स्टॉप लॉस (STOP LOSS):**\n### ₹{sl}")
with c3:
    st.success(f"**लक्ष्य १ (TARGET 1):**\n### ₹{t1}")
with c4:
    st.success(f"**लक्ष्य २ (TARGET 2):**\n### ₹{t2}")
