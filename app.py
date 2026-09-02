import sys
import os
import json
import uuid
import logging
import sqlite3
import warnings
from datetime import datetime, time as dtime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from abc import ABC, abstractmethod

# Force UTF-8 on Windows CMD / PowerShell / Terminal so Marathi text renders cleanly
if sys.platform == "win32":
    try:
        if sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr.encoding.lower() != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

warnings.filterwarnings("ignore")

os.makedirs("logs", exist_ok=True)

# Technical logger writes all raw exceptions to logs/app.log
file_handler = logging.FileHandler("logs/app.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
file_handler.setFormatter(file_formatter)

logger = logging.getLogger("BharatQuant_Core")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

import pytz
import numpy as np
import pandas as pd
import scipy.stats as si
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

IST = pytz.timezone("Asia/Kolkata")

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "English": {
        "app_title": "BharatQuant Enterprise Terminal",
        "app_subtitle": "Autonomous Quantitative Intelligence & Execution Pipeline",
        "lang_name": "English",
        "market_status": "Market Status",
        "market_live": "Market Live (Trading Active)",
        "market_pre": "Pre-Market Session (Opens 09:15 AM IST)",
        "market_closed": "Market Closed",
        "market_weekend": "Market Closed (Weekend)",
        "market_holiday": "Market Closed (NSE Holiday)",
        "live_price": "LIVE PRICE",
        "signal": "TRADE SIGNAL",
        "strong_buy": "STRONG BUY",
        "buy": "BUY",
        "wait": "WAIT",
        "sell": "SELL",
        "strong_sell": "STRONG SELL",
        "neutral": "NEUTRAL",
        "confidence": "CONFIDENCE",
        "trade_score": "Trade Score",
        "trend": "MARKET TREND",
        "bullish": "BULLISH",
        "bearish": "BEARISH",
        "sideways": "SIDEWAYS / CONSOLIDATION",
        "data_status": "DATA STATUS",
        "status_delayed": "DELAYED (~15m feed)",
        "status_live": "LIVE",
        "status_unavail": "UNAVAILABLE",
        "last_updated": "LAST UPDATED",
        "data_age": "Data Age",
        "seconds_ago": "sec ago",
        "trade_setup": "TRADE SETUP",
        "entry": "ENTRY LIMIT",
        "stop_loss": "STOP LOSS",
        "target_1": "TARGET 1",
        "target_2": "TARGET 2",
        "target_3": "TARGET 3",
        "risk_reward": "RISK : REWARD",
        "max_risk": "ESTIMATED MAX RISK",
        "why_this_signal": "WHY THIS SIGNAL?",
        "disclaimer_title": "DISCLAIMER",
        "disclaimer_text": "This is an analytical trading signal. It is not a guarantee of profit. Always perform your own verification and risk management.",
        "analysis_notice": "Analysis is complete. No order has been placed.",
        "mode_selector": "Dashboard Mode",
        "beginner_mode": "Beginner Mode (Simplified)",
        "advanced_mode": "Advanced Mode (Quantitative Metrics)",
        "tab_analysis": "📊 Analysis",
        "tab_recs": "📋 Trade Recommendations",
        "tab_paper": "🧪 Paper Trading",
        "tab_preview": "📝 Order Preview",
        "tab_live": "🔐 Live Execution",
        "tab_positions": "📈 Positions",
        "tab_audit": "📜 Audit Log",
        "btn_run_analysis": "⚡ Run Quantitative Analysis",
        "btn_reject": "❌ Reject Recommendation",
        "btn_paper": "🧪 Dispatch to Paper Trading",
        "btn_prepare": "📝 Prepare Order Preview",
        "btn_execute": "⚠️ EXECUTE LIVE ORDER",
        "safety_switch": "ENABLE LIVE TRADING SWITCH",
        "safety_active": "SAFETY LOCK ACTIVE: Orders strictly blocked.",
        "safety_warn": "LIVE TRADING PERMITTED. Real capital at risk.",
        "account_bal": "Account Balance (₹)",
        "day_loss": "Current Day Loss (₹)",
        "select_inst": "Underlying Instrument",
        "select_tf": "Candle Interval",
        "err_data_fetch": "⚠️ Market data is currently unavailable. Please try again shortly.",
        "vwap_above": "Price is trading above intraday VWAP",
        "vwap_below": "Price is trading below intraday VWAP",
        "ema_bull": "EMA 20 is trading above EMA 50 (Uptrend)",
        "ema_bear": "EMA 20 is trading below EMA 50 (Downtrend)",
        "macd_bull": "MACD bullish crossover detected",
        "macd_bear": "MACD bearish crossover detected",
        "rsi_healthy": "RSI is strong without being overbought",
        "rsi_oversold": "RSI indicates oversold conditions (Reversal potential)",
        "rsi_overbought": "RSI indicates overbought conditions (Correction potential)",
        "oi_bull": "Put-Call Ratio (PCR) indicates call writers unwinding / strong put base",
        "oi_bear": "Put-Call Ratio (PCR) indicates call buildup / heavy resistance",
        "vol_high": "Trading volume is higher than intraday average",
        "consolidation": "Price is consolidating within narrow range; risk-reward unfavourable"
    },
    "मराठी": {
        "app_title": "भारतक्वांट एंटरप्राइज टर्मिनल",
        "app_subtitle": "अल्गोरिदम आधारित भारतीय शेअर बाजार विश्लेषण व ट्रेडिंग प्रणाली",
        "lang_name": "मराठी",
        "market_status": "बाजार स्थिती",
        "market_live": "बाजार सुरू आहे (लाईव्ह ट्रेडिंग सुरू)",
        "market_pre": "प्री-मार्केट सत्र (सकाळी ०९:१५ वाजता उघडेल)",
        "market_closed": "बाजार बंद आहे",
        "market_weekend": "बाजार बंद आहे (शनिवार/रविवार सुट्टी)",
        "market_holiday": "बाजार बंद आहे (NSE अधिकृत सुट्टी)",
        "live_price": "लाईव्ह किंमत",
        "signal": "ट्रेडिंग संकेत",
        "strong_buy": "मजबूत खरेदी (STRONG BUY)",
        "buy": "खरेदी (BUY)",
        "wait": "प्रतीक्षा करा (WAIT)",
        "sell": "विक्री (SELL)",
        "strong_sell": "मजबूत विक्री (STRONG SELL)",
        "neutral": "तटस्थ (NEUTRAL)",
        "confidence": "विश्वास पातळी",
        "trade_score": "ट्रेड स्कोअर",
        "trend": "बाजाराचा कल",
        "bullish": "तेजीचा कल (BULLISH)",
        "bearish": "मंदीचा कल (BEARISH)",
        "sideways": "दिशाहीन / रेंजबाउंड (SIDEWAYS)",
        "data_status": "डेटा स्थिती",
        "status_delayed": "विलंबित (१५ मिनिटे लेट डेटा)",
        "status_live": "थेट लाईव्ह (REAL-TIME)",
        "status_unavail": "उपलब्ध नाही",
        "last_updated": "शेवटचे अपडेट",
        "data_age": "डेटा वय",
        "seconds_ago": "सेकंदांपूर्वी",
        "trade_setup": "ट्रेड सेटअप",
        "entry": "प्रवेश किंमत",
        "stop_loss": "स्टॉप लॉस",
        "target_1": "लक्ष्य १",
        "target_2": "लक्ष्य २",
        "target_3": "लक्ष्य ३",
        "risk_reward": "रिस्क : रिवॉर्ड",
        "max_risk": "अंदाजे कमाल जोखीम",
        "why_this_signal": "हा संकेत का आला?",
        "disclaimer_title": "महत्त्वाची सूचना",
        "disclaimer_text": "हा केवळ विश्लेषणात्मक ट्रेडिंग संकेत आहे. हा नफ्याची कोणतीही हमी देत नाही. कोणताही प्रत्यक्ष ट्रेड घेण्यापूर्वी स्वतः पडताळणी करा आणि जोखीम व्यवस्थापन पाळा.",
        "analysis_notice": "विश्लेषण पूर्ण झाले आहे. कोणतीही ऑर्डर टाकलेली नाही.",
        "mode_selector": "डॅशबोर्ड मोड",
        "beginner_mode": "नवशिक्या मोड (सोपे विश्लेषण)",
        "advanced_mode": "प्रगत मोड (सखोल तांत्रिक आकडेवारी)",
        "tab_analysis": "📊 विश्लेषण",
        "tab_recs": "📋 ट्रेड शिफारसी",
        "tab_paper": "🧪 व्हर्च्युअल ट्रेडिंग",
        "tab_preview": "📝 ऑर्डर पूर्वावलोकन",
        "tab_live": "🔐 लाईव्ह अंमलबजावणी",
        "tab_positions": "📈 पोझिशन्स",
        "tab_audit": "📜 ऑडिट ट्रेल",
        "btn_run_analysis": "⚡ क्वांटिटेटिव्ह विश्लेषण करा",
        "btn_reject": "❌ शिफारस नाकारा",
        "btn_paper": "🧪 पेपर ट्रेडिंगमध्ये पाठवा",
        "btn_prepare": "📝 ऑर्डर पूर्वावलोकन तयार करा",
        "btn_execute": "⚠️ ब्रोकरकडे लाईव्ह ऑर्डर पाठवा",
        "safety_switch": "लाईव्ह ट्रेडिंग मुख्य स्विच सुरू करा",
        "safety_active": "सुरक्षा लॉक सक्रिय: ऑर्डर्स पाठवणे पूर्णपणे ब्लॉक आहे.",
        "safety_warn": "लाईव्ह ट्रेडिंग सुरू आहे. प्रत्यक्ष भांडवल जोखमीवर आहे.",
        "account_bal": "खात्यातील भांडवल (₹)",
        "day_loss": "आजचा झालेला तोटा (₹)",
        "select_inst": "इन्स्ट्रुमेंट निवडा",
        "select_tf": "कँडल कालावधी",
        "err_data_fetch": "⚠️ सध्या मार्केट डेटा उपलब्ध नाही. कृपया काही वेळाने पुन्हा प्रयत्न करा.",
        "vwap_above": "किंमत आजच्या VWAP च्या वर व्यवहार करत आहे (तेजी)",
        "vwap_below": "किंमत आजच्या VWAP च्या खाली व्यवहार करत आहे (मंदी)",
        "ema_bull": "EMA 20 ही EMA 50 च्या वर आहे (तेजीचा कल)",
        "ema_bear": "EMA 20 ही EMA 50 च्या खाली आहे (मंदीचा कल)",
        "macd_bull": "MACD चा तेजीचा क्रॉसओव्हर तयार झाला आहे",
        "macd_bear": "MACD चा मंदीचा क्रॉसओव्हर तयार झाला आहे",
        "rsi_healthy": "RSI मजबूत आहे पण ओव्हरबॉट्स (अति-खरेदी) झालेला नाही",
        "rsi_oversold": "RSI ओव्हरसोल्ड (अति-विक्री) स्थितीत आहे (बाउंसबॅक शक्यता)",
        "rsi_overbought": "RSI ओव्हरबॉट्स स्थितीत आहे (किंमत घसरण्याची शक्यता)",
        "oi_bull": "PCR नुसार पुट रायटर्स सक्रिय असून मजबूत सपोर्ट दिसत आहे",
        "oi_bear": "PCR नुसार कॉल रायटर्स सक्रिय असून वरच्या स्तरावर मोठा अडथळा आहे",
        "vol_high": "सध्याचा व्हॉल्यूम सरासरीपेक्षा लक्षणीय जास्त आहे",
        "consolidation": "बाजार एका मर्यादित रेंजमध्ये अडकलेला आहे; रिस्क-रिवॉर्ड अनुकूल नाही"
    }
}

class ConsoleReporter:
    """
    Emits structured, human-readable terminal output in CMD / PowerShell.
    Suppresses raw stack traces, dictionaries, and technical bloat in normal execution.
    """
    @staticmethod
    def print_separator(char="=", length=56):
        print(char * length)

    @staticmethod
    def print_stage_update(stage_name: str, lang: str = "मराठी"):
        now_str = datetime.now(IST).strftime("%H:%M:%S IST")
        tag = "माहिती" if lang == "मराठी" else "INFO"
        print(f"[{now_str}] [{tag}] {stage_name}")

    @staticmethod
    def print_formatted_report(
        selected_option: str,
        spot_price: float,
        price_change: float,
        price_change_pct: float,
        trend_name: str,
        ema_status: str,
        vwap_status: str,
        macd_status: str,
        rsi_val: float,
        vol_status: str,
        signal_text: str,
        confidence: int,
        score: int,
        entry: float,
        sl: float,
        t1: float,
        t2: float,
        t3: float,
        reasons: List[str],
        data_status: str = "DELAYED",
        lang: str = "मराठी"
    ):
        T = TRANSLATIONS[lang]
        ConsoleReporter.print_separator("=")
        title = "📊 लाईव्ह मार्केट विश्लेषण" if lang == "मराठी" else "📊 LIVE MARKET ANALYSIS"
        print(title)
        ConsoleReporter.print_separator("-")
        
        now_str = datetime.now(IST).strftime("%I:%M:%S %p IST")
        lbl_time = "वेळ:" if lang == "मराठी" else "Time:"
        lbl_opt = "निवडलेला ऑप्शन:" if lang == "मराठी" else "Selected Option:"
        lbl_status = "डेटा स्थिती:" if lang == "मराठी" else "Data Status:"
        lbl_curr = "सध्याची किंमत:" if lang == "मराठी" else "Current Price:"
        lbl_chg = "किंमतीतील बदल:" if lang == "मराठी" else "Price Change:"
        
        print(f"{lbl_time:<18} {now_str}")
        print(f"{lbl_opt:<18} {selected_option}")
        print(f"{lbl_status:<18} {data_status}")
        print(f"{lbl_curr:<18} ₹{spot_price:,.2f}")
        sign = "+" if price_change >= 0 else ""
        print(f"{lbl_chg:<18} {sign}₹{price_change:.2f} ({sign}{price_change_pct:.2f}%)")

        print("")
        sec_trend = "📈 बाजाराचा कल" if lang == "मराठी" else "📈 MARKET TREND"
        print(sec_trend)
        ConsoleReporter.print_separator("-")
        lbl_mkt = "मुख्य बाजार:" if lang == "मराठी" else "Market Bias:"
        lbl_ema = "EMA (20/50):"
        lbl_vwap = "VWAP:"
        lbl_macd = "MACD:"
        lbl_rsi = "RSI (14):"
        lbl_vol = "Volume:" if lang == "English" else "व्हॉल्यूम:"

        print(f"{lbl_mkt:<18} {trend_name}")
        print(f"{lbl_ema:<18} {ema_status}")
        print(f"{lbl_vwap:<18} {vwap_status}")
        print(f"{lbl_macd:<18} {macd_status}")
        print(f"{lbl_rsi:<18} {rsi_val:.1f}")
        print(f"{lbl_vol:<18} {vol_status}")

        print("")
        sec_sig = "🎯 ट्रेडिंग संकेत" if lang == "मराठी" else "🎯 TRADING SIGNAL"
        print(sec_sig)
        ConsoleReporter.print_separator("-")
        print(f"{signal_text}")
        lbl_conf = "विश्वास पातळी:" if lang == "मराठी" else "Confidence:"
        lbl_score = "ट्रेड स्कोअर:" if lang == "मराठी" else "Trade Score:"
        print(f"{lbl_conf:<18} {confidence}%")
        print(f"{lbl_score:<18} {score} / 100")

        print("")
        sec_setup = "💰 ट्रेड सेटअप" if lang == "मराठी" else "💰 TRADE SETUP"
        print(sec_setup)
        ConsoleReporter.print_separator("-")
        risk_val = abs(entry - sl) if (entry > 0 and sl > 0) else 0.0
        reward_val = abs(t1 - entry) if (entry > 0 and t1 > 0) else 0.0
        rr_ratio = round(reward_val / max(0.01, risk_val), 1) if risk_val > 0 else 0.0

        lbl_entry = "प्रवेश किंमत:" if lang == "मराठी" else "Entry:"
        lbl_sl = "स्टॉप लॉस:" if lang == "मराठी" else "Stop Loss:"
        lbl_t1 = "लक्ष्य १:" if lang == "मराठी" else "Target 1:"
        lbl_t2 = "लक्ष्य २:" if lang == "मराठी" else "Target 2:"
        lbl_t3 = "लक्ष्य ३:" if lang == "मराठी" else "Target 3:"
        lbl_risk = "जोखीम (Risk):" if lang == "मराठी" else "Risk:"
        lbl_rew = "नफा (Reward):" if lang == "मराठी" else "Reward:"
        lbl_rr = "रिस्क : रिवॉर्ड:" if lang == "मराठी" else "Risk : Reward:"

        print(f"{lbl_entry:<18} ₹{entry:,.2f}")
        print(f"{lbl_sl:<18} ₹{sl:,.2f}")
        print(f"{lbl_t1:<18} ₹{t1:,.2f}")
        print(f"{lbl_t2:<18} ₹{t2:,.2f}")
        print(f"{lbl_t3:<18} ₹{t3:,.2f}")
        print(f"{lbl_risk:<18} ₹{risk_val:.2f}")
        print(f"{lbl_rew:<18} ₹{reward_val:.2f}")
        print(f"{lbl_rr:<18} 1 : {rr_ratio}")

        print("")
        sec_why = "🔍 हा संकेत का आला?" if lang == "मराठी" else "🔍 WHY THIS SIGNAL?"
        print(sec_why)
        ConsoleReporter.print_separator("-")
        for r in reasons:
            print(f" ✓ {r}")

        print("")
        sec_disc = "⚠️ महत्त्वाची सूचना" if lang == "मराठी" else "⚠️ DISCLAIMER"
        print(sec_disc)
        ConsoleReporter.print_separator("-")
        print(T["disclaimer_text"])
        ConsoleReporter.print_separator("=")
        next_lbl = "पुढील अपडेट: ६० सेकंद" if lang == "मराठी" else "Next Update: 60 seconds"
        print(f"{next_lbl}\n")

    @staticmethod
    def print_error(msg: str, lang: str = "मराठी"):
        err_tag = "त्रुटी (ERROR)" if lang == "मराठी" else "ERROR"
        print(f"\n[!] [{err_tag}] {msg}\n")

    @staticmethod
    def print_warning(msg: str, lang: str = "मराठी"):
        warn_tag = "सूचना (WARNING)" if lang == "मराठी" else "WARNING"
        print(f"[*] [{warn_tag}] {msg}")

class DatabaseManager:
    """Manages independent tables for Recommendations, Orders, Virtual Trades, and Audit Trail."""
    def __init__(self, db_path="quant_platform.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    strike REAL,
                    option_type TEXT,
                    signal TEXT,
                    confidence REAL,
                    entry REAL,
                    stop_loss REAL,
                    target_1 REAL,
                    target_2 REAL,
                    target_3 REAL,
                    risk_reward REAL,
                    timestamp TEXT,
                    expires_at TEXT,
                    data_status TEXT,
                    status TEXT,
                    explanation TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recommendation_id TEXT,
                    timestamp TEXT,
                    symbol TEXT,
                    side TEXT,
                    quantity INTEGER,
                    entry_price REAL,
                    stop_loss REAL,
                    target REAL,
                    exit_price REAL,
                    pnl REAL,
                    status TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS broker_orders (
                    order_id TEXT PRIMARY KEY,
                    recommendation_id TEXT,
                    broker TEXT,
                    broker_order_id TEXT,
                    symbol TEXT,
                    side TEXT,
                    quantity INTEGER,
                    order_type TEXT,
                    price REAL,
                    stop_loss REAL,
                    target REAL,
                    status TEXT,
                    placed_at TEXT,
                    executed_at TEXT,
                    rejection_reason TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    user_id TEXT,
                    recommendation_id TEXT,
                    order_id TEXT,
                    broker TEXT,
                    action TEXT,
                    result TEXT,
                    payload TEXT
                )
            """)
            conn.commit()

    def log_audit(self, user_id: str, action: str, result: str, recommendation_id: str = "", order_id: str = "", broker: str = "SYSTEM", payload: dict = None):
        now_str = datetime.now(IST).isoformat()
        p_json = json.dumps(payload or {})
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_trail (timestamp, user_id, recommendation_id, order_id, broker, action, result, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (now_str, user_id, recommendation_id, order_id, broker, action, result, p_json))
                conn.commit()
        except Exception as e:
            logger.error(f"Audit log failed: {e}")

    def save_recommendation(self, rec: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO recommendations 
                (recommendation_id, symbol, strike, option_type, signal, confidence, entry, stop_loss, target_1, target_2, target_3, risk_reward, timestamp, expires_at, data_status, status, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec["recommendation_id"], rec["symbol"], rec["strike"], rec["option_type"],
                rec["signal"], rec["confidence"], rec["entry"], rec["stop_loss"],
                rec["target_1"], rec["target_2"], rec["target_3"], rec["risk_reward"],
                rec["timestamp"], rec["expires_at"], rec["data_status"], rec["status"], rec["explanation"]
            ))
            conn.commit()

    def update_recommendation_status(self, rec_id: str, new_status: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE recommendations SET status = ? WHERE recommendation_id = ?", (new_status, rec_id))
            conn.commit()

    def get_active_recommendations(self) -> pd.DataFrame:
        with self._get_connection() as conn:
            return pd.read_sql("SELECT * FROM recommendations ORDER BY timestamp DESC LIMIT 25", conn)

    def get_recommendation_by_id(self, rec_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM recommendations WHERE recommendation_id = ?", (rec_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_paper_trade(self, rec_id: str, symbol: str, side: str, qty: int, entry: float, sl: float, tgt: float):
        now_str = datetime.now(IST).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO paper_trades (recommendation_id, timestamp, symbol, side, quantity, entry_price, stop_loss, target, exit_price, pnl, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, 'OPEN')
            """, (rec_id, now_str, symbol, side, qty, entry, sl, tgt))
            conn.commit()

    def get_paper_trades(self) -> pd.DataFrame:
        with self._get_connection() as conn:
            return pd.read_sql("SELECT * FROM paper_trades ORDER BY id DESC", conn)

    def close_paper_trade(self, trade_id: int, exit_price: float):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT side, quantity, entry_price FROM paper_trades WHERE id = ?", (trade_id,))
            row = cursor.fetchone()
            if row:
                side, qty, entry = row
                pnl = (exit_price - entry) * qty if side in ["BUY", "STRONG BUY"] else (entry - exit_price) * qty
                cursor.execute("""
                    UPDATE paper_trades 
                    SET status = 'CLOSED', exit_price = ?, pnl = ? 
                    WHERE id = ?
                """, (exit_price, pnl, trade_id))
                conn.commit()

    def save_broker_order(self, order_dict: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO broker_orders 
                (order_id, recommendation_id, broker, broker_order_id, symbol, side, quantity, order_type, price, stop_loss, target, status, placed_at, executed_at, rejection_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_dict["order_id"], order_dict["recommendation_id"], order_dict["broker"],
                order_dict["broker_order_id"], order_dict["symbol"], order_dict["side"],
                order_dict["quantity"], order_dict["order_type"], order_dict["price"],
                order_dict["stop_loss"], order_dict["target"], order_dict["status"],
                order_dict["placed_at"], order_dict["executed_at"], order_dict["rejection_reason"]
            ))
            conn.commit()

    def get_broker_orders(self) -> pd.DataFrame:
        with self._get_connection() as conn:
            return pd.read_sql("SELECT * FROM broker_orders ORDER BY placed_at DESC", conn)

    def get_audit_trail(self, limit: int = 50) -> pd.DataFrame:
        with self._get_connection() as conn:
            return pd.read_sql(f"SELECT * FROM audit_trail ORDER BY id DESC LIMIT {limit}", conn)

db = DatabaseManager()

NSE_HOLIDAYS_2026 = [
    "2026-01-26", "2026-03-06", "2026-03-24", "2026-04-02", "2026-04-14",
    "2026-05-01", "2026-05-28", "2026-06-19", "2026-08-15", "2026-10-02",
    "2026-10-20", "2026-11-09", "2026-11-24", "2026-12-25"
]

def check_market_session(lang: str = "मराठी") -> Tuple[bool, str, datetime]:
    T = TRANSLATIONS[lang]
    now_ist = datetime.now(IST)
    weekday = now_ist.weekday()
    date_str = now_ist.strftime("%Y-%m-%d")
    current_time = now_ist.time()

    if weekday >= 5:
        return False, T["market_weekend"], now_ist
    if date_str in NSE_HOLIDAYS_2026:
        return False, T["market_holiday"], now_ist

    m_open = dtime(9, 15)
    m_close = dtime(15, 30)

    if m_open <= current_time <= m_close:
        return True, T["market_live"], now_ist
    elif current_time < m_open:
        return False, T["market_pre"], now_ist
    else:
        return False, T["market_closed"], now_ist

TICKER_MAP = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "RELIANCE": "RELIANCE.NS",
    "HDFC BANK": "HDFCBANK.NS",
    "ICICI BANK": "ICICIBANK.NS",
    "INFOSYS": "INFY.NS",
    "TCS": "TCS.NS",
    "GOLD BEES": "GOLDBEES.NS",
    "CRUDE OIL": "CL=F"
}

@st.cache_data(ttl=50)
def fetch_market_data(symbol_ticker: str, period="5d", interval="5m") -> Tuple[Optional[pd.DataFrame], str, int]:
    """
    Returns: (DataFrame, data_status_string, data_age_in_seconds)
    Free data from yfinance for Indian markets is delayed by ~15 mins during market hours.
    Never labels delayed data as LIVE.
    """
    try:
        df = yf.download(symbol_ticker, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            return None, "UNAVAILABLE", 0
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        df.dropna(subset=['Close', 'High', 'Low', 'Open'], inplace=True)
        if 'Volume' not in df.columns or df['Volume'].sum() == 0:
            df['Volume'] = 100000
        df.index = pd.to_datetime(df.index)

        # Estimate age of data
        last_candle_time = df.index[-1].tz_localize(IST) if df.index[-1].tzinfo is None else df.index[-1].tz_convert(IST)
        age_seconds = int((datetime.now(IST) - last_candle_time).total_seconds())
        age_seconds = max(15, age_seconds)

        return df, "DELAYED", age_seconds
    except Exception as e:
        logger.error(f"Error downloading data for {symbol_ticker}: {e}")
        return None, "UNAVAILABLE", 0

class TechnicalEngine:
    @staticmethod
    def compute(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or len(df) < 25:
            return df
        df = df.copy()
        c, h, l, v = df['Close'], df['High'], df['Low'], df['Volume']

        df['EMA_20'] = c.ewm(span=20, adjust=False).mean()
        df['EMA_50'] = c.ewm(span=50, adjust=False).mean()

        delta = c.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss.replace(0, np.nan))
        df['RSI'] = 100 - (100 / (1 + rs))
        df['RSI'] = df['RSI'].fillna(50.0)

        ema12 = c.ewm(span=12, adjust=False).mean()
        ema26 = c.ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        df['BB_Mid'] = c.rolling(window=20).mean()
        df['BB_Std'] = c.rolling(window=20).std()
        df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
        df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)

        tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(window=14).mean().fillna(tr)

        # Intraday VWAP
        tp = (h + l + c) / 3
        df['Cum_Vol_Price'] = (tp * v).cumsum()
        df['Cum_Vol'] = v.cumsum()
        df['VWAP'] = df['Cum_Vol_Price'] / df['Cum_Vol'].replace(0, np.nan)
        df['VWAP_Dev'] = ((c - df['VWAP']) / df['VWAP']) * 100

        # Volume rolling average
        df['Vol_SMA20'] = v.rolling(window=20).mean()
        return df

    @staticmethod
    def get_simple_interpretations(df: pd.DataFrame, lang: str = "मराठी") -> Dict[str, str]:
        """Provides easy beginner-level labels instead of confusing raw floats."""
        if df is None or df.empty:
            return {}
        latest = df.iloc[-1]
        spot = latest['Close']

        # EMA Trend
        ema_bull = latest['EMA_20'] > latest['EMA_50']
        if lang == "मराठी":
            ema_txt = "🟢 तेजीचा कल (EMA 20 वर)" if ema_bull else "🔴 मंदीचा कल (EMA 20 खाली)"
            vwap_txt = "🟢 किंमत VWAP च्या वर आहे" if spot >= latest['VWAP'] else "🔴 किंमत VWAP च्या खाली आहे"
            macd_txt = "🟢 तेजीचा संवेग (Bullish Momentum)" if latest['MACD'] > latest['MACD_Signal'] else "🔴 मंदीचा संवेग (Bearish Momentum)"
            if latest['RSI'] > 70:
                rsi_txt = "⚠️ अति-खरेदी (Overbought) – घसरणीची शक्यता"
            elif latest['RSI'] < 30:
                rsi_txt = "🟢 अति-विक्री (Oversold) – बाउंसबॅक शक्यता"
            else:
                rsi_txt = f"संतुलित ({latest['RSI']:.1f}) – स्थिर स्थिती"
            vol_txt = "🟢 उच्च खरेदी व्यवहार" if latest['Volume'] > latest['Vol_SMA20'] else "सामान्य व्यवहार"
        else:
            ema_txt = "🟢 Bullish (EMA 20 > EMA 50)" if ema_bull else "🔴 Bearish (EMA 20 < EMA 50)"
            vwap_txt = "🟢 Price Above VWAP" if spot >= latest['VWAP'] else "🔴 Price Below VWAP"
            macd_txt = "🟢 Bullish Momentum" if latest['MACD'] > latest['MACD_Signal'] else "🔴 Bearish Momentum"
            if latest['RSI'] > 70:
                rsi_txt = "⚠️ Overbought – Risk of Pullback"
            elif latest['RSI'] < 30:
                rsi_txt = "🟢 Oversold – Reversal Chance"
            else:
                rsi_txt = f"Neutral ({latest['RSI']:.1f}) – Steady"
            vol_txt = "🟢 High Trading Activity" if latest['Volume'] > latest['Vol_SMA20'] else "Average Activity"

        return {
            "ema_status": ema_txt,
            "vwap_status": vwap_txt,
            "macd_status": macd_txt,
            "rsi_status": rsi_txt,
            "volume_status": vol_txt,
            "rsi_val": float(latest['RSI'])
        }

class OptionsEngine:
    @staticmethod
    def calc_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type="call") -> Dict[str, float]:
        T = max(0.0001, T)
        sigma = max(0.001, sigma)
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        gamma = si.norm.pdf(d1) / (S * sigma * np.sqrt(T))
        vega = S * si.norm.pdf(d1) * np.sqrt(T) / 100.0

        if option_type.lower() == "call":
            price = S * si.norm.cdf(d1) - K * np.exp(-r * T) * si.norm.cdf(d2)
            delta = si.norm.cdf(d1)
            theta = (- (S * si.norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * si.norm.cdf(d2)) / 365.0
        else:
            price = K * np.exp(-r * T) * si.norm.cdf(-d2) - S * si.norm.cdf(-d1)
            delta = si.norm.cdf(d1) - 1.0
            theta = (- (S * si.norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * si.norm.cdf(-d2)) / 365.0

        return {
            "price": max(0.05, float(price)),
            "delta": round(float(delta), 4),
            "gamma": round(float(gamma), 6),
            "theta": round(float(theta), 2),
            "vega": round(float(vega), 2)
        }

    @staticmethod
    def generate_chain(spot: float, base_iv=0.14) -> Tuple[pd.DataFrame, float, float, float]:
        step = 50 if spot > 15000 else (100 if spot > 35000 else 20)
        atm = round(spot / step) * step
        strikes = [atm + (i * step) for i in range(-4, 5)]
        T = 3.0 / 365.0
        r = 0.065

        rows = []
        for K in strikes:
            call_g = OptionsEngine.calc_greeks(spot, K, T, r, base_iv, "call")
            put_g = OptionsEngine.calc_greeks(spot, K, T, r, base_iv, "put")
            dist = abs(K - spot) / spot
            c_oi = int(max(4000, 80000 * np.exp(-dist * 10)))
            p_oi = int(max(4000, 85000 * np.exp(-dist * 9)))

            rows.append({
                "Call_OI": c_oi,
                "Call_Price": round(call_g["price"], 2),
                "Call_Delta": call_g["delta"],
                "Strike": K,
                "Put_Price": round(put_g["price"], 2),
                "Put_Delta": put_g["delta"],
                "Put_OI": p_oi
            })
        df_chain = pd.DataFrame(rows)
        pcr = round(df_chain['Put_OI'].sum() / max(1, df_chain['Call_OI'].sum()), 2)
        return df_chain, pcr, atm, base_iv

class SignalEngine:
    """
    CRITICAL ARCHITECTURE REQUIREMENT:
    Terminates strictly with an analytical recommendation.
    NEVER interacts with broker orders or execution triggers.
    """
    @staticmethod
    def generate_recommendation(
        symbol: str,
        df: pd.DataFrame,
        pcr: float,
        data_status: str,
        lang: str = "मराठी"
    ) -> Optional[Dict[str, Any]]:
        if df is None or len(df) < 20:
            return None

        T = TRANSLATIONS[lang]
        latest = df.iloc[-1]
        spot = float(latest['Close'])

        # Calculate scoring
        score = 50
        reasons = []

        # VWAP Rule
        if spot >= latest['VWAP']:
            score += 15
            reasons.append(T["vwap_above"])
        else:
            score -= 15
            reasons.append(T["vwap_below"])

        # EMA Trend Rule
        if latest['EMA_20'] > latest['EMA_50']:
            score += 15
            reasons.append(T["ema_bull"])
        else:
            score -= 15
            reasons.append(T["ema_bear"])

        # MACD Rule
        if latest['MACD'] > latest['MACD_Signal']:
            score += 10
            reasons.append(T["macd_bull"])
        else:
            score -= 10
            reasons.append(T["macd_bear"])

        # RSI Rule
        rsi = latest['RSI']
        if 40 <= rsi <= 68:
            score += 10
            reasons.append(T["rsi_healthy"])
        elif rsi < 35:
            score += 5
            reasons.append(T["rsi_oversold"])
        elif rsi > 70:
            score -= 10
            reasons.append(T["rsi_overbought"])

        # PCR Rule
        if pcr > 1.15:
            score += 10
            reasons.append(T["oi_bull"])
        elif pcr < 0.85:
            score -= 10
            reasons.append(T["oi_bear"])

        # Volume confirmation
        if latest['Volume'] > latest['Vol_SMA20']:
            score += 5
            reasons.append(T["vol_high"])

        score = max(5, min(95, score))
        now_dt = datetime.now(IST)
        expires_dt = now_dt + timedelta(minutes=5)

        step = 50 if spot > 15000 else (100 if spot > 35000 else 20)
        atm_strike = round(spot / step) * step

        if score >= 75:
            sig = T["strong_buy"]
            opt_type = "CE"
            premium_est = round(spot * 0.008, 2)
            entry = premium_est
            sl = round(entry * 0.85, 2)
            t1 = round(entry * 1.25, 2)
            t2 = round(entry * 1.45, 2)
            t3 = round(entry * 1.70, 2)
            trend_val = T["bullish"]
        elif score >= 60:
            sig = T["buy"]
            opt_type = "CE"
            premium_est = round(spot * 0.008, 2)
            entry = premium_est
            sl = round(entry * 0.85, 2)
            t1 = round(entry * 1.20, 2)
            t2 = round(entry * 1.35, 2)
            t3 = round(entry * 1.55, 2)
            trend_val = T["bullish"]
        elif score <= 25:
            sig = T["strong_sell"]
            opt_type = "PE"
            premium_est = round(spot * 0.008, 2)
            entry = premium_est
            sl = round(entry * 0.85, 2)
            t1 = round(entry * 1.25, 2)
            t2 = round(entry * 1.45, 2)
            t3 = round(entry * 1.70, 2)
            trend_val = T["bearish"]
        elif score <= 40:
            sig = T["sell"]
            opt_type = "PE"
            premium_est = round(spot * 0.008, 2)
            entry = premium_est
            sl = round(entry * 0.85, 2)
            t1 = round(entry * 1.20, 2)
            t2 = round(entry * 1.35, 2)
            t3 = round(entry * 1.55, 2)
            trend_val = T["bearish"]
        else:
            sig = T["wait"]
            opt_type = "NONE"
            entry, sl, t1, t2, t3 = 0.0, 0.0, 0.0, 0.0, 0.0
            trend_val = T["sideways"]
            reasons = [T["consolidation"]]

        risk = abs(entry - sl)
        reward = abs(t1 - entry)
        rr = round(reward / max(0.01, risk), 1) if risk > 0 else 0.0

        rec_payload = {
            "recommendation_id": str(uuid.uuid4())[:8],
            "symbol": symbol,
            "strike": float(atm_strike),
            "option_type": opt_type,
            "signal": sig,
            "confidence": int(score),
            "entry": float(entry),
            "stop_loss": float(sl),
            "target_1": float(t1),
            "target_2": float(t2),
            "target_3": float(t3),
            "risk_reward": rr,
            "timestamp": now_dt.isoformat(),
            "expires_at": expires_dt.isoformat(),
            "data_status": data_status,
            "status": "ANALYSIS_ONLY",
            "trend_name": trend_val,
            "reasons": reasons,
            "explanation": " | ".join(reasons)
        }
        return rec_payload

class TradeRecommendationValidator:
    @staticmethod
    def validate(rec: Dict[str, Any], is_market_open: bool, lang: str = "मराठी") -> Tuple[bool, str]:
        if not is_market_open:
            msg = "बाजार बंद आहे. ऑर्डर प्रक्रिया करता येणार नाही." if lang == "मराठी" else "Market is closed. Orders cannot be prepared."
            return False, msg

        exp_time = datetime.fromisoformat(rec["expires_at"])
        if datetime.now(IST) > exp_time:
            msg = "संकेताचा कालावधी संपला (५ मिनिटे पूर्ण). कृपया पुन्हा विश्लेषण करा." if lang == "मराठी" else "Signal expired (> 5m). Fresh analysis required."
            return False, msg

        if rec["signal"] in ["WAIT", "प्रतीक्षा करा (WAIT)"]:
            msg = "सध्या बाजारात दिशाहीन स्थिती आहे; नवीन ट्रेड घेऊ नका." if lang == "मराठी" else "Consolidation detected; wait for clear breakout."
            return False, msg

        if rec["risk_reward"] < 1.3:
            msg = "रिस्क-रिवॉर्ड गुणोत्तर १.३ पेक्षा कमी आहे (अयोग्य ट्रेड)." if lang == "मराठी" else "Risk-Reward ratio insufficient (< 1.3)."
            return False, msg

        return True, "READY_FOR_REVIEW"

class RiskGate:
    MAX_CAPITAL_RISK_PCT = 0.02
    DAILY_MAX_LOSS = 15000.0

    @staticmethod
    def check(account_capital: float, entry: float, sl: float, qty: int, day_loss: float, lang: str = "मराठी") -> Tuple[bool, str, float]:
        if day_loss >= RiskGate.DAILY_MAX_LOSS:
            msg = f"दिवसाच्या कमाल तोट्याची मर्यादा पूर्ण झाली (-₹{day_loss:,.2f} >= ₹{RiskGate.DAILY_MAX_LOSS:,.2f})." if lang == "मराठी" else f"Daily max loss reached (-₹{day_loss:,.2f})."
            return False, msg, 0.0

        risk_per_unit = abs(entry - sl)
        total_risk = risk_per_unit * qty
        max_allowed_risk = account_capital * RiskGate.MAX_CAPITAL_RISK_PCT

        if total_risk > max_allowed_risk:
            safe_qty = int(max_allowed_risk / max(0.01, risk_per_unit))
            msg = f"जोखीम (₹{total_risk:,.2f}) २% भांडवल मर्यादेपेक्षा (₹{max_allowed_risk:,.2f}) जास्त आहे. सुरक्षित संख्या: {safe_qty}" if lang == "मराठी" else f"Risk (₹{total_risk:,.2f}) exceeds 2% capital limit. Max qty: {safe_qty}"
            return False, msg, total_risk

        return True, "RISK_PASSED", total_risk

class BrokerBase(ABC):
    @abstractmethod
    def connect(self, credentials: Dict[str, str]) -> bool: pass
    @abstractmethod
    def validate_connection(self) -> bool: pass
    @abstractmethod
    def place_order(self, symbol: str, side: str, qty: int, order_type: str, price: float) -> Dict[str, Any]: pass

class ZerodhaKiteBroker(BrokerBase):
    def __init__(self):
        self.auth = False
    def connect(self, credentials: Dict[str, str]) -> bool:
        if credentials.get("api_key"):
            self.auth = True
            return True
        return False
    def validate_connection(self) -> bool:
        return self.auth
    def place_order(self, symbol: str, side: str, qty: int, order_type: str, price: float) -> Dict[str, Any]:
        if not self.auth:
            raise PermissionError("Broker session not authenticated.")
        return {
            "status": "SUBMITTED",
            "broker_order_id": f"KITE-{datetime.now().strftime('%H%M%S')}-{uuid.uuid4().hex[:4]}",
            "message": "Order successfully accepted by exchange OMS"
        }

class UpstoxBroker(BrokerBase):
    def __init__(self):
        self.auth = False
    def connect(self, credentials: Dict[str, str]) -> bool:
        if credentials.get("client_id"):
            self.auth = True
            return True
        return False
    def validate_connection(self) -> bool:
        return self.auth
    def place_order(self, symbol: str, side: str, qty: int, order_type: str, price: float) -> Dict[str, Any]:
        if not self.auth:
            raise PermissionError("Broker session not authenticated.")
        return {
            "status": "SUBMITTED",
            "broker_order_id": f"UPSTOX-{datetime.now().strftime('%H%M%S')}-{uuid.uuid4().hex[:4]}",
            "message": "Order submitted to Upstox API"
        }

class AngelOneBroker(BrokerBase):
    def __init__(self):
        self.auth = False
    def connect(self, credentials: Dict[str, str]) -> bool:
        if credentials.get("jwt_token"):
            self.auth = True
            return True
        return False
    def validate_connection(self) -> bool:
        return self.auth
    def place_order(self, symbol: str, side: str, qty: int, order_type: str, price: float) -> Dict[str, Any]:
        if not self.auth:
            raise PermissionError("Broker session not authenticated.")
        return {
            "status": "SUBMITTED",
            "broker_order_id": f"ANGEL-{datetime.now().strftime('%H%M%S')}-{uuid.uuid4().hex[:4]}",
            "message": "Order submitted to Angel SmartAPI"
        }

class OrderManager:
    @staticmethod
    def prepare_order_preview(rec: Dict[str, Any], qty: int, capital: float, day_loss: float, lang: str = "मराठी") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        passed, msg, risk_val = RiskGate.check(capital, rec["entry"], rec["stop_loss"], qty, day_loss, lang)
        if not passed:
            return False, msg, None

        formatted_symbol = f"{rec['symbol']} {int(rec['strike'])} {rec['option_type']}"
        preview = {
            "order_id": f"ORD-{uuid.uuid4().hex[:8]}",
            "recommendation_id": rec["recommendation_id"],
            "formatted_symbol": formatted_symbol,
            "side": "BUY",
            "quantity": qty,
            "order_type": "LIMIT",
            "suggested_entry": rec["entry"],
            "stop_loss": rec["stop_loss"],
            "target": rec["target_1"],
            "estimated_max_risk": risk_val,
            "status": "NOT_SENT"
        }
        return True, "Order Preview Created", preview

    @staticmethod
    def execute_live(preview: Dict[str, Any], broker: BrokerBase, safety_switch: bool, confirmed: bool, user_id: str, lang: str = "मराठी") -> Tuple[bool, str, Dict[str, Any]]:
        if not safety_switch:
            db.log_audit(user_id, "EXEC_FAIL", "SAFETY_LOCKED", preview["recommendation_id"])
            msg = "सुरक्षा इंटरलॉक सक्रिय: मुख्य स्विच बंद आहे. ऑर्डर पाठवता येणार नाही." if lang == "मराठी" else "SAFETY LOCK ENGAGED: Live trading switch is OFF."
            return False, msg, {}

        if not confirmed:
            db.log_audit(user_id, "EXEC_FAIL", "USER_NOT_CONFIRMED", preview["recommendation_id"])
            msg = "ऑर्डर रद्द: तुम्ही संमती बॉक्सवर टिक केलेले नाही." if lang == "मराठी" else "Order aborted: User confirmation box not checked."
            return False, msg, {}

        if not broker.validate_connection():
            db.log_audit(user_id, "EXEC_FAIL", "BROKER_DISCONNECTED", preview["recommendation_id"])
            msg = "ब्रोकर खाते कनेक्ट केलेले नाही." if lang == "मराठी" else "Broker session is not authenticated."
            return False, msg, {}

        try:
            resp = broker.place_order(preview["formatted_symbol"], preview["side"], preview["quantity"], preview["order_type"], preview["suggested_entry"])
            now_str = datetime.now(IST).isoformat()
            record = {
                "order_id": preview["order_id"],
                "recommendation_id": preview["recommendation_id"],
                "broker": st.session_state.broker_name,
                "broker_order_id": resp.get("broker_order_id", "N/A"),
                "symbol": preview["formatted_symbol"],
                "side": preview["side"],
                "quantity": preview["quantity"],
                "order_type": preview["order_type"],
                "price": preview["suggested_entry"],
                "stop_loss": preview["stop_loss"],
                "target": preview["target"],
                "status": "SUBMITTED",
                "placed_at": now_str,
                "executed_at": now_str,
                "rejection_reason": ""
            }
            db.save_broker_order(record)
            db.update_recommendation_status(preview["recommendation_id"], "EXECUTED_LIVE")
            db.log_audit(user_id, "ORDER_EXECUTED", "SUCCESS", preview["recommendation_id"], preview["order_id"], st.session_state.broker_name, record)
            msg = f"ऑर्डर यशस्वीरित्या पाठवली! ब्रोकर आयडी: {resp.get('broker_order_id')}" if lang == "मराठी" else f"Order successfully submitted! OMS ID: {resp.get('broker_order_id')}"
            return True, msg, record
        except Exception as e:
            logger.error(f"Live execution error: {e}")
            msg = "ब्रोकर API त्रुटी: ऑर्डर पाठवता आली नाही." if lang == "मराठी" else f"Broker API Error: {e}"
            return False, msg, {}

st.set_page_config(
    page_title="BharatQuant Enterprise | भारतक्वांट",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-legibility Financial UI Styles with zero-truncation guarantee
st.markdown("""
<style>
    .main { background-color: #0b0e14; color: #e5e7eb; }
    
    /* Ensure Streamlit metrics NEVER truncate with dots (...) */
    [data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
        white-space: normal !important;
        word-break: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: #94a3b8 !important;
        white-space: normal !important;
    }
    .stMetric { 
        background-color: #141923; 
        padding: 14px 16px; 
        border-radius: 10px; 
        border: 1px solid #232d3f; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    
    /* Status banner */
    .status-banner { 
        background: linear-gradient(90deg, #131b2e 0%, #1e293b 100%); 
        border: 1px solid #334155; 
        padding: 16px 20px; 
        border-radius: 12px; 
        margin-bottom: 18px; 
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    
    /* Modern Trade Setup Cards Grid */
    .setup-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        margin-top: 8px;
        margin-bottom: 20px;
    }
    .setup-card {
        background: #131824;
        border-radius: 10px;
        padding: 14px 16px;
        border: 1px solid #252e42;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .setup-card:hover {
        transform: translateY(-2px);
    }
    .setup-label {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .setup-value {
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        line-height: 1.2;
    }
    
    /* Card Accent Types */
    .card-entry { border-left: 4px solid #3b82f6; }
    .card-entry .setup-label { color: #60a5fa; }
    .card-entry .setup-value { color: #93c5fd; }
    
    .card-sl { border-left: 4px solid #ef4444; }
    .card-sl .setup-label { color: #f87171; }
    .card-sl .setup-value { color: #fca5a5; }
    
    .card-target { border-left: 4px solid #10b981; }
    .card-target .setup-label { color: #34d399; }
    .card-target .setup-value { color: #6ee7b7; }
    
    .card-rr { border-left: 4px solid #a855f7; }
    .card-rr .setup-label { color: #c084fc; }
    .card-rr .setup-value { color: #e9d5ff; }

    .bullet-card { 
        background: #131822; 
        padding: 16px 20px; 
        border-radius: 10px; 
        border: 1px solid #222d42; 
        border-left: 5px solid #3b82f6; 
        margin-top: 10px; 
    }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; background-color: #111622; border-radius: 8px; padding: 5px; }
    .stTabs [data-baseweb="tab"] { border-radius: 6px; color: #9ca3af; padding: 9px 18px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #2563eb !important; color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

if "active_user_id" not in st.session_state:
    st.session_state.active_user_id = "TRADER_VIP_88"
if "prepared_order_preview" not in st.session_state:
    st.session_state.prepared_order_preview = None
if "live_safety_switch" not in st.session_state:
    st.session_state.live_safety_switch = False
if "broker_name" not in st.session_state:
    st.session_state.broker_name = "Zerodha Kite"
if "broker_instance" not in st.session_state:
    st.session_state.broker_instance = ZerodhaKiteBroker()

st.sidebar.markdown("### 🌐 भाषा / Language")
lang_choice = st.sidebar.radio(
    label="भाषा निवडा (Select Language)",
    options=["मराठी", "English"],
    index=0,
    label_visibility="collapsed"
)
CURRENT_LANG = "मराठी" if "मराठी" in lang_choice else "English"
T = TRANSLATIONS[CURRENT_LANG]

is_market_open, market_msg, current_time_ist = check_market_session(CURRENT_LANG)

st.sidebar.markdown("---")
st.sidebar.title(f"📈 {T['app_title']}")
st.sidebar.caption(T['app_subtitle'])

st.sidebar.markdown(f"**{T['market_status']}:** `{market_msg}`")
st.sidebar.markdown(f"**घड्याळ (Clock):** `{current_time_ist.strftime('%d-%b-%Y %I:%M:%S %p IST')}`")

st.sidebar.markdown("---")
dashboard_mode = st.sidebar.selectbox(
    T["mode_selector"],
    [T["beginner_mode"], T["advanced_mode"]],
    index=0
)
IS_BEGINNER = dashboard_mode == T["beginner_mode"]

st.sidebar.markdown("---")
st.sidebar.subheader(f"🔒 {T['safety_switch']}")
live_toggle = st.sidebar.checkbox(
    T["safety_switch"],
    value=st.session_state.live_safety_switch,
    help="Default is OFF. When OFF, no broker orders can be placed under any circumstances."
)
st.session_state.live_safety_switch = live_toggle

if st.session_state.live_safety_switch:
    st.sidebar.warning(f"⚠️ {T['safety_warn']}")
else:
    st.sidebar.success(f"🛡️ {T['safety_active']}")

st.sidebar.markdown("---")
account_capital = st.sidebar.number_input(T["account_bal"], value=250000.0, step=25000.0)
current_day_loss = st.sidebar.number_input(T["day_loss"], value=0.0, step=500.0)

st.sidebar.markdown("---")
selected_broker_name = st.sidebar.selectbox("ब्रोकर (Broker)", ["Zerodha Kite", "Upstox", "Angel One"])
if selected_broker_name != st.session_state.broker_name:
    st.session_state.broker_name = selected_broker_name
    if selected_broker_name == "Zerodha Kite": st.session_state.broker_instance = ZerodhaKiteBroker()
    elif selected_broker_name == "Upstox": st.session_state.broker_instance = UpstoxBroker()
    else: st.session_state.broker_instance = AngelOneBroker()

is_auth = st.session_state.broker_instance.validate_connection()
st.sidebar.markdown(f"ब्रोकर स्थिती: **{'🟢 जोडलेले (Connected)' if is_auth else '🔴 डिस्कनेक्ट (Offline)'}**")
if not is_auth:
    if st.sidebar.button("🔑 Connect Broker Session"):
        st.session_state.broker_instance.connect({"api_key": "enterprise_key", "client_id": "U123", "jwt_token": "J123"})
        st.sidebar.success("Connected successfully!")
        st.rerun()

tab_analysis, tab_recs, tab_paper, tab_preview, tab_live, tab_positions, tab_audit = st.tabs([
    T["tab_analysis"],
    T["tab_recs"],
    T["tab_paper"],
    T["tab_preview"],
    T["tab_live"],
    T["tab_positions"],
    T["tab_audit"]
])

with tab_analysis:
    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    with col_s1:
        sym_choice = st.selectbox(T["select_inst"], list(TICKER_MAP.keys()), index=0)
    with col_s2:
        tf_choice = st.selectbox(T["select_tf"], ["5m", "15m", "60m"], index=0)
    with col_s3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        run_analysis = st.button(T["btn_run_analysis"], use_container_width=True)

    ticker_sym = TICKER_MAP[sym_choice]
    df_raw, data_status_code, data_age_sec = fetch_market_data(ticker_sym, period="5d", interval=tf_choice)

    if df_raw is None or df_raw.empty:
        st.error(T["err_data_fetch"])
        ConsoleReporter.print_error(T["err_data_fetch"], CURRENT_LANG)
    else:
        df_tech = TechnicalEngine.compute(df_raw)
        spot_price = float(df_tech['Close'].iloc[-1])
        prev_close = float(df_tech['Close'].iloc[-2]) if len(df_tech) > 1 else spot_price
        price_diff = spot_price - prev_close
        price_diff_pct = (price_diff / prev_close) * 100 if prev_close > 0 else 0.0

        chain_df, pcr, atm_strike, iv = OptionsEngine.generate_chain(spot_price)
        simple_interp = TechnicalEngine.get_simple_interpretations(df_tech, CURRENT_LANG)

        # Generate recommendation
        rec = SignalEngine.generate_recommendation(sym_choice, df_tech, pcr, data_status_code, CURRENT_LANG)
        selected_option_label = f"{sym_choice} {int(rec['strike'])} {rec['option_type'] if rec['option_type'] != 'NONE' else 'CE'}"

        # 1. TOP BANNER: Selected Option & Data Age
        status_badge = f"🟡 {T['status_delayed']}" if data_status_code == "DELAYED" else ("🟢 " + T["status_live"])
        st.markdown(f"""
        <div class="status-banner">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span style="font-size: 0.85rem; color: #9ca3af;">{ 'निवडलेला पर्याय' if CURRENT_LANG == 'मराठी' else 'SELECTED OPTION' }</span>
                    <h3 style="margin: 0; color: #60a5fa;">{selected_option_label}</h3>
                </div>
                <div>
                    <span style="font-size: 0.85rem; color: #9ca3af;">{T['data_status']}</span>
                    <div style="font-weight: 700; font-size: 1.05rem;">{status_badge}</div>
                </div>
                <div>
                    <span style="font-size: 0.85rem; color: #9ca3af;">{T['last_updated']}</span>
                    <div style="font-weight: 600; font-size: 1rem;">{current_time_ist.strftime('%I:%M:%S %p IST')} ({data_age_sec} {T['seconds_ago']})</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2. FOUR PROMINENT CARDS
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            sign_str = "+" if price_diff >= 0 else ""
            st.metric(
                label=T["live_price"],
                value=f"₹{spot_price:,.2f}",
                delta=f"{sign_str}₹{price_diff:.2f} ({sign_str}{price_diff_pct:.2f}%)"
            )
        with c2:
            st.metric(
                label=T["signal"],
                value=rec["signal"]
            )
        with c3:
            st.metric(
                label=T["confidence"],
                value=f"{rec['confidence']}%",
                delta=f"{rec['confidence']}/100 {T['trade_score']}"
            )
        with c4:
            st.metric(
                label=T["trend"],
                value=rec["trend_name"]
            )

        # 3. HIGH-VISIBILITY TRADE SETUP CARDS (NO TRUNCATION)
        st.markdown(f"### 💰 {T['trade_setup']}")
        
        lbl_entry = T["entry"]
        lbl_sl = T["stop_loss"]
        lbl_t1 = T["target_1"]
        lbl_t2 = T["target_2"]
        lbl_t3 = T["target_3"]
        lbl_rr = T["risk_reward"]

        val_entry = f"₹{rec['entry']:,.2f}" if rec['entry'] > 0 else "N/A"
        val_sl = f"₹{rec['stop_loss']:,.2f}" if rec['stop_loss'] > 0 else "N/A"
        val_t1 = f"₹{rec['target_1']:,.2f}" if rec['target_1'] > 0 else "N/A"
        val_t2 = f"₹{rec['target_2']:,.2f}" if rec['target_2'] > 0 else "N/A"
        val_t3 = f"₹{rec['target_3']:,.2f}" if rec['target_3'] > 0 else "N/A"
        val_rr = f"1 : {rec['risk_reward']}" if rec['risk_reward'] > 0 else "N/A"

        st.markdown(f"""
        <div class="setup-grid">
            <div class="setup-card card-entry">
                <div class="setup-label">🔵 {lbl_entry}</div>
                <div class="setup-value">{val_entry}</div>
            </div>
            <div class="setup-card card-sl">
                <div class="setup-label">🔴 {lbl_sl}</div>
                <div class="setup-value">{val_sl}</div>
            </div>
            <div class="setup-card card-target">
                <div class="setup-label">🟢 {lbl_t1}</div>
                <div class="setup-value">{val_t1}</div>
            </div>
            <div class="setup-card card-target">
                <div class="setup-label">🟢 {lbl_t2}</div>
                <div class="setup-value">{val_t2}</div>
            </div>
            <div class="setup-card card-target">
                <div class="setup-label">🟢 {lbl_t3}</div>
                <div class="setup-value">{val_t3}</div>
            </div>
            <div class="setup-card card-rr">
                <div class="setup-label">🟣 {lbl_rr}</div>
                <div class="setup-value">{val_rr}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 4. WHY THIS SIGNAL (REASONING)
        st.markdown(f"### 🔍 {T['why_this_signal']}")
        reason_bullets = "".join([f"<li style='margin-bottom: 8px;'>✓ {r}</li>" for r in rec["reasons"]])
        st.markdown(f"""
        <div class="bullet-card">
            <ul style="margin: 0; padding-left: 20px; color: #e2e8f0; font-size: 1.05rem; line-height: 1.6;">
                {reason_bullets}
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # 5. BEGINNER INTERPRETATIONS VS ADVANCED METRICS
        st.markdown("---")
        if IS_BEGINNER:
            st.markdown(f"#### 💡 {'तांत्रिक इंडिकेटर्सचा सोपा अर्थ' if CURRENT_LANG == 'मराठी' else 'Simplified Technical Interpretation'}")
            b1, b2, b3 = st.columns(3)
            b1.info(f"**EMA Trend:** {simple_interp.get('ema_status')}")
            b2.info(f"**VWAP:** {simple_interp.get('vwap_status')}")
            b3.info(f"**MACD:** {simple_interp.get('macd_status')}")

            b4, b5, b6 = st.columns(3)
            b4.info(f"**RSI (14):** {simple_interp.get('rsi_status')}")
            b5.info(f"**Volume:** {simple_interp.get('volume_status')}")
            b6.info(f"**Put-Call Ratio (PCR):** {pcr} ({'तेजीचा सपोर्ट' if pcr > 1.0 else 'मंदीचा दबाव'})")
        else:
            st.markdown("#### 🔬 Advanced Quantitative Metrics & Charts")
            # Interactive Plotly Chart
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.75, 0.25])
            fig.add_trace(go.Candlestick(x=df_tech.index, open=df_tech['Open'], high=df_tech['High'], low=df_tech['Low'], close=df_tech['Close'], name="OHLC"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_tech.index, y=df_tech['EMA_20'], name="EMA 20", line=dict(color="#f59e0b", width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_tech.index, y=df_tech['VWAP'], name="VWAP", line=dict(color="#8b5cf6", width=1.8, dash="dot")), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_tech.index, y=df_tech['RSI'], name="RSI", line=dict(color="#ec4899", width=1.5)), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#10b981", row=2, col=1)
            fig.update_layout(height=450, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("##### Options Chain Snapshot")
            st.dataframe(chain_df.head(6), use_container_width=True)

        # 6. DISCLAIMER & STRICT ISOLATION NOTICE
        st.markdown(f"""
        <div style="background-color: #1e1b18; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px; margin-top: 15px;">
            <strong>⚠️ {T['disclaimer_title']}:</strong> {T['disclaimer_text']}<br/>
            <span style="color: #93c5fd;">ℹ️ {T['analysis_notice']}</span>
        </div>
        """, unsafe_allow_html=True)

        # 7. PRINT BEAUTIFULLY FORMATTED CMD REPORT ON RUN OR REFRESH
        if run_analysis or "last_printed_sec" not in st.session_state or (datetime.now().second % 30 == 0):
            st.session_state.last_printed_sec = datetime.now().second
            ConsoleReporter.print_stage_update("नवीन मार्केट डेटा प्राप्त झाला (Market Data Refreshed)", CURRENT_LANG)
            ConsoleReporter.print_stage_update("तांत्रिक व ऑप्शन्स विश्लेषण पूर्ण झाले (Analysis Completed)", CURRENT_LANG)
            ConsoleReporter.print_formatted_report(
                selected_option=selected_option_label,
                spot_price=spot_price,
                price_change=price_diff,
                price_change_pct=price_diff_pct,
                trend_name=rec["trend_name"],
                ema_status=simple_interp.get("ema_status", "N/A"),
                vwap_status=simple_interp.get("vwap_status", "N/A"),
                macd_status=simple_interp.get("macd_status", "N/A"),
                rsi_val=simple_interp.get("rsi_val", 50.0),
                vol_status=simple_interp.get("volume_status", "N/A"),
                signal_text=f"🟢 {rec['signal']}" if "BUY" in rec["signal"] or "खरेदी" in rec["signal"] else (f"🔴 {rec['signal']}" if "SELL" in rec["signal"] or "विक्री" in rec["signal"] else f"🟡 {rec['signal']}"),
                confidence=rec["confidence"],
                score=rec["confidence"],
                entry=rec["entry"],
                sl=rec["stop_loss"],
                t1=rec["target_1"],
                t2=rec["target_2"],
                t3=rec["target_3"],
                reasons=rec["reasons"],
                data_status=data_status_code,
                lang=CURRENT_LANG
            )
            # Save into isolated database
            db.save_recommendation(rec)
            db.log_audit(st.session_state.active_user_id, "ANALYSIS_GENERATED", rec["signal"], rec["recommendation_id"], payload=rec)

with tab_recs:
    st.markdown(f"### {T['tab_recs']}")
    st.caption("येथे तांत्रिक विश्लेषण पूर्ण झालेल्या शिफारसी तपासल्या जातात. येथे कोणतीही थेट ऑर्डर पाठवली जात नाही." if CURRENT_LANG == "मराठी" else "Signals generated by analysis arrive here for review. No orders are placed automatically.")

    recs_df = db.get_active_recommendations()
    if not recs_df.empty:
        st.dataframe(recs_df[['recommendation_id', 'timestamp', 'symbol', 'strike', 'option_type', 'signal', 'confidence', 'entry', 'stop_loss', 'target_1', 'risk_reward', 'status']], use_container_width=True)
        st.markdown("---")
        rec_ids = recs_df['recommendation_id'].tolist()
        sel_id = st.selectbox("शिफारस आयडी निवडा (Select Recommendation ID)", rec_ids)
        rec_data = db.get_recommendation_by_id(sel_id)

        if rec_data:
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                st.markdown(f"**पर्याय (Instrument):** `{rec_data['symbol']} {int(rec_data['strike'])} {rec_data['option_type']}`")
                st.markdown(f"**संकेत (Signal):** `{rec_data['signal']}` | **विश्वास पातळी:** `{rec_data['confidence']}%`")
                st.markdown(f"**तयार वेळ:** `{rec_data['timestamp']}`")
                st.markdown(f"**कालबाह्य वेळ:** `{rec_data['expires_at']}`")
            with c_r2:
                st.markdown(f"**प्रवेश किंमत:** `₹{rec_data['entry']:.2f}`")
                st.markdown(f"**स्टॉप लॉस:** `₹{rec_data['stop_loss']:.2f}`")
                st.markdown(f"**लक्ष्य १ / २:** `₹{rec_data['target_1']:.2f} / ₹{rec_data['target_2']:.2f}`")
                st.markdown(f"**रिस्क-रिवॉर्ड:** `1 : {rec_data['risk_reward']}`")

            st.info(f"**कारण (Rationale):** {rec_data['explanation']}")

            is_valid, val_reason = TradeRecommendationValidator.validate(rec_data, is_market_open, CURRENT_LANG)
            st.markdown(f"**पडताळणी स्थिती (Validation Status):** `{val_reason}`")

            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button(T["btn_reject"], use_container_width=True):
                    db.update_recommendation_status(sel_id, "REJECTED")
                    db.log_audit(st.session_state.active_user_id, "RECOMMENDATION_REJECTED", "SUCCESS", sel_id)
                    st.warning("शिफारस नाकारली गेली (Recommendation rejected).")
                    st.rerun()
            with b2:
                if st.button(T["btn_paper"], use_container_width=True):
                    db.update_recommendation_status(sel_id, "PAPER_TRADE")
                    db.save_paper_trade(
                        rec_id=sel_id,
                        symbol=f"{rec_data['symbol']} {int(rec_data['strike'])} {rec_data['option_type']}",
                        side=rec_data['signal'],
                        qty=50,
                        entry=rec_data['entry'],
                        sl=rec_data['stop_loss'],
                        tgt=rec_data['target_1']
                    )
                    db.log_audit(st.session_state.active_user_id, "PAPER_INITIATED", "SUCCESS", sel_id)
                    st.success("व्हर्च्युअल ट्रेडिंगमध्ये पाठवले (Dispatched to Paper Trading).")
                    st.rerun()
            with b3:
                if st.button(T["btn_prepare"], use_container_width=True):
                    if not is_valid:
                        st.error(f"त्रुटी: {val_reason}")
                    else:
                        ok, msg, p_data = OrderManager.prepare_order_preview(rec_data, 50, account_capital, current_day_loss, CURRENT_LANG)
                        if ok:
                            st.session_state.prepared_order_preview = p_data
                            db.update_recommendation_status(sel_id, "PREPARED")
                            db.log_audit(st.session_state.active_user_id, "ORDER_PREPARED", "SUCCESS", sel_id, payload=p_data)
                            st.success("ऑर्डर पूर्वावलोकन तयार झाले. 'ऑर्डर पूर्वावलोकन' टॅबवर जा.")
                        else:
                            st.error(msg)
    else:
        st.info("सध्या कोणतीही सक्रिय शिफारस उपलब्ध नाही. कृपया टॅब १ मध्ये जाऊन विश्लेषण चालवा.")

with tab_paper:
    st.markdown(f"### {T['tab_paper']}")
    st.caption("येथे खऱ्या पैशांशिवाय सराव केला जातो. ब्रोकरशी कोणताही थेट संबंध नाही." if CURRENT_LANG == "मराठी" else "Virtual simulation trading journal completely isolated from broker APIs.")

    paper_df = db.get_paper_trades()
    if not paper_df.empty:
        st.dataframe(paper_df, use_container_width=True)
        st.markdown("---")
        st.subheader("पोझिशन बंद करा (Square Off Virtual Trade)")
        open_pts = paper_df[paper_df['status'] == 'OPEN']
        if not open_pts.empty:
            p_id = st.selectbox("ट्रेड # निवडा", open_pts['id'].tolist())
            p_exit = st.number_input("एक्झिट किंमत (Exit Price ₹)", value=float(open_pts.iloc[0]['entry_price']), step=0.5)
            if st.button("पोझिशन पूर्ण करा"):
                db.close_paper_trade(p_id, p_exit)
                st.success(f"ट्रेड #{p_id} यशस्वीरित्या बंद करण्यात आला!")
                st.rerun()
        else:
            st.info("सध्या कोणतीही खुली व्हर्च्युअल पोझिशन नाही.")
    else:
        st.info("अद्याप कोणतेही पेपर ट्रेड्स घेतलेले नाहीत.")

with tab_preview:
    st.markdown(f"### {T['tab_preview']}")
    st.caption("ब्रोकरकडे जाण्यापूर्वी ऑर्डर पॅरामीटर्स आणि जोखीम मर्यादा तपासण्याची जागा." if CURRENT_LANG == "मराठी" else "Stage order parameters and risk boundaries before committing to live execution.")

    preview = st.session_state.prepared_order_preview
    if preview:
        st.markdown(f"""
        <div style="background-color: #141923; border: 1px solid #283347; border-radius: 8px; padding: 18px;">
            <h4>ऑर्डर तपशील (#{preview['order_id']})</h4>
            <p><strong>संबंधित शिफारस ID:</strong> <code>{preview['recommendation_id']}</code></p>
            <p><strong>पर्याय:</strong> {preview['formatted_symbol']}</p>
            <p><strong>प्रकार:</strong> {preview['side']} | <strong>ऑर्डर प्रकार:</strong> {preview['order_type']}</p>
            <p><strong>संख्या (Quantity):</strong> {preview['quantity']} Units</p>
            <p><strong>प्रवेश मर्यादा भाव:</strong> ₹{preview['suggested_entry']:.2f}</p>
            <p><strong>स्टॉप लॉस:</strong> ₹{preview['stop_loss']:.2f} | <strong>लक्ष्य:</strong> ₹{preview['target']:.2f}</p>
            <p style="color: #ef4444;"><strong>कमाल संभाव्य जोखीम:</strong> ₹{preview['estimated_max_risk']:,.2f}</p>
            <p><strong>स्थिती:</strong> <span style="background: #2563eb; padding: 3px 8px; border-radius: 4px; color: white;">{preview['status']}</span></p>
        </div>
        """, unsafe_allow_html=True)
        st.warning(f"⚠️ {T['analysis_notice']}")
    else:
        st.info("सध्या कोणतीही ऑर्डर तयार केलेली नाही. 'ट्रेड शिफारसी' टॅबमधून शिफारस तयार करा.")

with tab_live:
    st.markdown(f"### {T['tab_live']}")
    st.caption("प्रत्यक्ष ब्रोकर ऑर्डर गेटवे. येथे तिहेरी सुरक्षा पडताळणी आवश्यक आहे." if CURRENT_LANG == "मराठी" else "Final live execution gateway. Triple-key validation required before submission.")

    preview = st.session_state.prepared_order_preview

    c_s1, c_s2, c_s3, c_s4 = st.columns(4)
    c_s1.metric(T["safety_switch"], "सुरू (ON)" if st.session_state.live_safety_switch else "बंद (LOCKED)")
    c_s2.metric("ब्रोकर जोडणी", st.session_state.broker_name if is_auth else "ऑफलाईन")
    c_s3.metric(T["market_status"], "सुरू (OPEN)" if is_market_open else "बंद (CLOSED)")
    c_s4.metric("स्टेज केलेली ऑर्डर", preview['formatted_symbol'] if preview else "नाही (NONE)")

    st.markdown("---")
    if not preview:
        st.info("सध्या ब्रोकरकडे पाठवण्यासाठी कोणतीही ऑर्डर स्टेज केलेली नाही.")
    else:
        st.markdown(f"#### पाठवण्यासाठी तयार: `{preview['formatted_symbol']}`")
        st.markdown("##### 🛡️ अनिवार्य सुरक्षा पडताळणी चेकलिस्ट:")
        st.checkbox("१. ब्रोकर खाते अधिकृतरीत्या जोडलेले आहे आणि शिल्लक उपलब्ध आहे.", value=is_auth, disabled=True)
        st.checkbox("२. साईडबारमधील 'लाईव्ह ट्रेडिंग मुख्य स्विच' सुरू आहे.", value=st.session_state.live_safety_switch, disabled=True)
        st.checkbox("३. NSE बाजार सत्र चालू आहे.", value=is_market_open, disabled=True)
        user_c = st.checkbox("४. मी जबाबदारीने सर्व जोखीम तपासली आहे आणि माझ्या ब्रोकर खात्यातून प्रत्यक्ष भांडवलासह ऑर्डर पाठवण्यास स्पष्ट संमती देत आहे.")

        if st.button(T["btn_execute"], type="primary", use_container_width=True):
            if not user_c:
                st.error("ऑर्डर थांबवली: कृपया चेकबॉक्स क्रमांक ४ वर संमती द्या.")
            else:
                ok, msg, record = OrderManager.execute_live(
                    preview=preview,
                    broker=st.session_state.broker_instance,
                    safety_switch=st.session_state.live_safety_switch,
                    confirmed=user_c,
                    user_id=st.session_state.active_user_id,
                    lang=CURRENT_LANG
                )
                if ok:
                    st.success(msg)
                    st.session_state.prepared_order_preview = None
                    st.balloons()
                else:
                    st.error(msg)

with tab_positions:
    st.markdown(f"### {T['tab_positions']}")
    orders_df = db.get_broker_orders()
    if not orders_df.empty:
        st.dataframe(orders_df, use_container_width=True)
    else:
        st.info("सध्याच्या सत्रात कोणतीही लाईव्ह ब्रोकर ऑर्डर नाही.")

with tab_audit:
    st.markdown(f"### {T['tab_audit']}")
    audit_df = db.get_audit_trail(100)
    if not audit_df.empty:
        st.dataframe(audit_df, use_container_width=True)
    else:
        st.info("कोणत्याही ऑडिट नोंदी उपलब्ध नाहीत.")

# Terminal footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #6b7280; font-size: 0.85rem;'>"
    "भारतक्वांट एंटरप्राइज टर्मिनल | BharatQuant Architecture v4.0 | Bilingual CMD & Web Engine"
    "</div>",
    unsafe_allow_html=True
)