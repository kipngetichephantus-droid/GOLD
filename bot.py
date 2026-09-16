import os, requests, datetime
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

now_utc = datetime.datetime.now(timezone.utc)
now_eat = now_utc.astimezone(datetime.timezone(datetime.timedelta(hours=3)))
weekday = now_utc.weekday()
hour_utc = now_utc.hour

# Market closed check
if weekday == 5 or (weekday == 6 and hour_utc < 22):
    if hour_utc % 6 == 0:
        send("🔴 *MARKET CLOSED*\nGold closed for weekend.\nOpens Mon 1:00 AM EAT")
    exit()

def get_data(ticker, period="5d", interval="15m"):
    try:
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
        if df.empty or len(df) < 50:
            print(f"{ticker} empty")
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print(f"Data error {ticker}: {e}")
        return None

# FIXED: Spot Gold first, Futures fallback
gold = get_data("XAUUSD=X")
if gold is None:
    print("XAUUSD=X failed, using GC=F fallback")
    gold = get_data("GC=F")

dxy = get_data("DX-Y.NYB", period="5d", interval="1h")

if gold is None:
    send("⚠️ Data error - Yahoo blocked, will retry next 15min")
    exit()

close = float(gold['Close'].iloc[-1])
high = float(gold['High'].iloc[-1])
low = float(gold['Low'].iloc[-1])
prev_high = float(gold['High'].tail(20).max())
prev_low = float(gold['Low'].tail(20).min())
recent_low = float(gold['Low'].tail(6).min())
recent_high = float(gold['High'].tail(6).max())

delta = gold['Close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
rs = gain / loss
rsi = 100 - (100 / (1 + rs))
rsi_now = float(rsi.iloc[-1])

dxy_trend = "neutral"
if dxy is not None and len(dxy) > 10:
    dxy_close = float(dxy['Close'].iloc[-1])
    dxy_prev = float(dxy['Close'].iloc[-5])
    dxy_trend = "up" if dxy_close > dxy_prev else "down"

signal = None
sl = tp = 0
reason = ""

if close < (prev_low + 3) and close > recent_low and rsi_now < 48 and dxy_trend == "down":
    sl = recent_low - 3.0
    risk = close - sl
    if 2.5 <= risk <= 10:
        tp = close + (risk * 2.2)
        signal = "BUY"
        reason = f"Sweep Low + DXY Bearish + RSI {rsi_now:.1f}"
elif close > (prev_high - 3) and close < recent_high and rsi_now > 52 and dxy_trend == "up":
    sl = recent_high + 3.0
    risk = sl - close
    if 2.5 <= risk <= 10:
        tp = close - (risk * 2.2)
        signal = "SELL"
        reason = f"Sweep High + DXY Bullish + RSI {rsi_now:.1f}"

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
*Time:* {now_eat.strftime('%a %H:%M EAT')}

⚠️ Demo signal - Manage risk!
"""
    send(msg)
else:
    send(f"⏳ *Scanning... No 80% setup yet*\nGold: {close:.2f} | RSI: {rsi_now:.1f} | DXY: {dxy_trend}\nLow: {recent_low:.2f} High: {recent_high:.2f}\nNext check in 15min")
