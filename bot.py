import requests, yfinance as yf, pandas as pd, datetime, os
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
def send(m):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": m, "parse_mode": "Markdown"}, timeout=15)
def get():
    try:
        g = yf.download("GC=F", period="5d", interval="15m", auto_adjust=True, progress=False, threads=False)
        if len(g)<20: return None
        c=float(g['Close'].iloc[-1]); lo=float(g['Low'].tail(20).min()); hi=float(g['High'].tail(20).max())
        if c>lo+4:
            sl=float(g['Low'].tail(6).min())-2.5
            if 2<(c-sl)<12: return f"🟢 *BUY XAUUSD 80%*\nEntry: {c:.2f}\nSL: {sl:.2f}\nTP: {c+(c-sl)*2:.2f}"
        if c<hi-4:
            sl=float(g['High'].tail(6).max())+2.5
            if 2<(sl-c)<12: return f"🔴 *SELL XAUUSD 80%*\nEntry: {c:.2f}\nSL: {sl:.2f}\nTP: {c-(sl-c)*2:.2f}"
    except: return None
s=get()
if s: send(s)
