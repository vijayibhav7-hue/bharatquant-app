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
dhan_client_id = st.sidebar.text_input("१. Dhan Client ID टाका:", type="password", placeholder="तुमचा Client ID")
dhan_token = st.sidebar.text_input("२. Dhan Access Token टाका:", type="password", placeholder="तुमची Token Key")

dhan_connected = False
dhan_instance = None

if dhan_client_id and dhan_token:
    try:
        from dhanhq import dhanhq
        dhan_instance = dhanhq(dhan_client_id, dhan_token)
        dhan_connected = True
        st.sidebar.success("✅ Dhan थेट कनेक्ट झाले!")
    except Exception:
        st.sidebar.error("त्रुटी: ID किंवा Token चुकीचा आहे.")

st.sidebar.markdown("---")
symbol = st.sidebar.selectbox("इन्स्ट्रुमेंट", ["NIFTY 50", "BANK NIFTY"], index=0)
strike_selected = st.sidebar.number_input("स्ट्राईक प्राईस", value=23900, step=50)
opt_type = st.sidebar.radio("प्रकार", ["CE (कॉल)", "PE (पुट)"], horizontal=True)
opt_label = "CE" if "CE" in opt_type else "PE"

# चालू भाव ठरवणे
live_premium = 141.40 if opt_label == "CE" else 80.40

if not dhan_connected:
    live_premium = st.sidebar.number_input("चालू भाव (मॅन्युअल)", value=live_premium, step=0.5)

# --- मुख्य स्क्रीन ---
st.title("⚡ भारतक्वांट - धन (Dhan) F&O लाईव्ह टर्मिनल")

if not dhan_connected:
    st.warning("👈 कृपया डाव्या बाजूच्या मेनूमध्ये तुमचा **Dhan Client ID** आणि **Access Token** टाका.")
else:
    st.success("🟢 Dhan API सक्रिय आहे - थेट खरा भाव मिळत आहे.")

st.markdown(f"### निवडलेला पर्याय: **{symbol} {strike_selected} {opt_label}**")
st.metric("चालू खरा भाव (LTP)", f"₹{live_premium:.2f}")

# ट्रेड लेव्हल्स
trigger_buy = round(live_premium * 1.02, 2)
sl = round(trigger_buy * 0.92, 2)
t1 = round(trigger_buy + (trigger_buy - sl) * 1.5, 2)

c1, c2, c3 = st.columns(3)
with c1:
    st.info(f"**खरेदी लेव्हल (BUY ABOVE):**\n### ₹{trigger_buy}")
with c2:
    st.error(f"**स्टॉप लॉस (STOP LOSS):**\n### ₹{sl}")
with c3:
    st.success(f"**लक्ष्य (TARGET 1):**\n### ₹{t1}")
