import os, requests, datetime
from datetime import timezone, timedelta
import yfinance as yf
import pandas as pd

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=20)
    except Exception as e:
        print(f"Send error: {e}")

now_utc = datetime.datetime.now(timezone.utc)
now_eat = now_utc.astimezone(timezone(timedelta(hours=3)))
weekday = now_utc.weekday()
hour_utc = now_utc.hour

if weekday == 5 or (weekday == 6 and hour_utc < 22):
    if hour_utc % 6 == 0:
        send("🔴 *MARKET CLOSED*\nGold closed for weekend.")
    exit()

def get_spot():
    try:
        r = requests.get("https://data-asg.goldprice.org/dbXRates/USD", timeout=10).json()
        return float(r['items'][0]['xauPrice'])
    except:
        try:
            r = requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()
            return float(r['price'])
        except:
            return None

def get_hist(ticker, period="5d", interval="15m"):
    try:
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

spot = get_spot()
hist = get_hist("GC=F")
if spot is None or hist is None:
    send("⚠️ Data error - retry 15min")
    exit()

close = spot
recent_low = float(hist['Low'].tail(6).min()) - 30
recent_high = float(hist['High'].tail(6).max()) - 30
prev_high = float(hist['High'].tail(20).max()) - 30
prev_low = float(hist['Low'].tail(20).min()) - 30

delta = hist['Close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
rsi = 100 - (100 / (1 + gain/loss))
rsi_now = float(rsi.iloc[-1])

dxy_hist = get_hist("DX-Y.NYB", period="5d", interval="1h")
dxy_trend = "neutral"
if dxy_hist is not None:
    dxy_trend = "up" if float(dxy_hist['Close'].iloc[-1]) > float(dxy_hist['Close'].iloc[-5]) else "down"

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
    send(f"{emoji} *{signal} XAUUSD NOW 80%*\n\n*Entry:* {close:.2f} (SPOT)\n*SL:* {sl:.2f}\n*TP:* {tp:.2f}\n*Reason:* {reason}\n*Time:* {now_eat.strftime('%a %H:%M EAT')}")
else:
    send(f"⏳ *Scanning... No setup*\nGold SPOT: {close:.2f} | RSI: {rsi_now:.1f} | DXY: {dxy_trend}\nLow: {recent_low:.2f} High: {recent_high:.2f}")



