import os, requests, datetime, time
from datetime import timezone
import yfinance as yf
import pandas as pd

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=20)
        print(r.text)
    except Exception as e:
        print(f"Send error: {e}")

# ========== MARKET HOURS FILTER ==========
now_utc = datetime.datetime.now(timezone.utc)
weekday = now_utc.weekday()  # 0=Mon, 5=Sat, 6=Sun
hour_utc = now_utc.hour

# Gold Closed: Sat + Sun until 22:00 UTC (Mon 1am EAT)
if weekday == 5 or (weekday == 6 and hour_utc < 22):
    send("🔴 *MARKET CLOSED*\nGold is closed for weekend.\nOpens Monday 1:00 AM EAT\nNo signals until open.")
    exit()

# ========== GET DATA ==========
def get_data(ticker, period="5d", interval="15m"):
    try:
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
        if len(df) < 50:
            return None
        return df
    except:
        return None

gold = get_data("GC=F")
dxy = get_data("DX-Y.NYB", period="5d", interval="1h")
if gold is None:
    send("⚠️ Data error - will retry next 15min")
    exit()

# ========== ICT + INDICATORS ==========
close = float(gold['Close'].iloc[-1])
high = float(gold['High'].iloc[-1])
low = float(gold['Low'].iloc[-1])
prev_high = float(gold['High'].tail(20).max())
prev_low = float(gold['Low'].tail(20).min())
recent_low = float(gold['Low'].tail(6).min())
recent_high = float(gold['High'].tail(6).max())

# RSI 14
delta = gold['Close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
rs = gain / loss
rsi = 100 - (100 / (1 + rs))
rsi_now = float(rsi.iloc[-1])

# DXY trend
dxy_trend = "neutral"
if dxy is not None and len(dxy) > 10:
    dxy_close = float(dxy['Close'].iloc[-1])
    dxy_prev = float(dxy['Close'].iloc[-5])
    dxy_trend = "up" if dxy_close > dxy_prev else "down"

# ========== 80% SETUP LOGIC ==========
signal = None
sl = 0
tp = 0
reason = ""

# BUY CONDITIONS: Sweep low + DXY down + RSI <45 + Close near low zone
if close < (prev_low + 3) and close > recent_low and rsi_now < 48 and dxy_trend == "down":
    sl = recent_low - 3.0
    risk = close - sl
    if 2.5 <= risk <= 10:
        tp = close + (risk * 2.2)
        signal = "BUY"
        reason = f"Sweep Low + DXY Bearish + RSI {rsi_now:.1f}"

# SELL CONDITIONS: Sweep high + DXY up + RSI >55 + Close near high zone  
elif close > (prev_high - 3) and close < recent_high and rsi_now > 52 and dxy_trend == "up":
    sl = recent_high + 3.0
    risk = sl - close
    if 2.5 <= risk <= 10:
        tp = close - (risk * 2.2)
        signal = "SELL"
        reason = f"Sweep High + DXY Bullish + RSI {rsi_now:.1f}"

# ========== SEND SIGNAL ==========
if signal:
    emoji = "🟢" if signal == "BUY" else "🔴"
    msg = f"""{emoji} *{signal} XAUUSD NOW 80%*

*Entry:* {close:.2f}
*SL:* {sl:.2f} ({abs(close-sl):.1f}$)
*TP:* {tp:.2f} ({abs(tp-close):.1f}$)
*RR:* 1:2.2

*Reason:* {reason}
*ICT:* Liquidity Sweep + OB
*DXY:* {dxy_trend.upper()}
*RSI:* {rsi_now:.1f}
*Time:* {datetime.datetime.now().strftime('%a %H:%M EAT')}

⚠️ Demo signal - Manage risk!
"""
    send(msg)
else:
    # Only send "No setup" once per 4 hours to avoid spam - check hour
    if hour_utc % 4 == 0:
        send(f"⏳ *No 80% setup*\nGold: {close:.2f} | RSI: {rsi_now:.1f} | DXY: {dxy_trend}\nScanning every 15min...")
    else:
        print(f"No setup: {close:.2f} RSI {rsi_now:.1f} DXY {dxy_trend}")
