import streamlit as st
import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import StochRSIIndicator
from datetime import datetime
import pytz
import time

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(page_title="Multi Asset Trading Dashboard", layout="wide")

REFRESH_SEC = 15
IST = pytz.timezone("Asia/Kolkata")

# -------------------------------
# DEFAULT SYMBOL LIST
# -------------------------------
if "symbols" not in st.session_state:
    st.session_state.symbols = {
        "Bank Nifty": "^NSEBANK",
        "Nifty 50": "^NSEI",
        "Bitcoin": "BTC-USD",
        "Ethereum": "ETH-USD"
    }

# -------------------------------
# SIDEBAR - SELECT SYMBOL
# -------------------------------
st.sidebar.header("📌 Select Instrument")

selected_name = st.sidebar.selectbox(
    "Choose Symbol",
    list(st.session_state.symbols.keys())
)

SYMBOL = st.session_state.symbols[selected_name]

# -------------------------------
# ADD NEW SYMBOL
# -------------------------------
st.sidebar.markdown("### ➕ Add New Symbol")

new_name = st.sidebar.text_input("Display Name")
new_symbol = st.sidebar.text_input("Yahoo Symbol (e.g. SOL-USD)")

if st.sidebar.button("Add Symbol"):
    if new_name and new_symbol:
        st.session_state.symbols[new_name] = new_symbol.upper()
        st.sidebar.success("Added Successfully")

# -------------------------------
# REMOVE SYMBOL
# -------------------------------
st.sidebar.markdown("### ➖ Remove Symbol")

remove_name = st.sidebar.selectbox(
    "Select to Remove",
    list(st.session_state.symbols.keys())
)

if st.sidebar.button("Remove Symbol"):
    if len(st.session_state.symbols) > 1:
        del st.session_state.symbols[remove_name]
        st.sidebar.success("Removed Successfully")
    else:
        st.sidebar.warning("At least one symbol required")

# -------------------------------
# DATA FUNCTION
# -------------------------------
@st.cache_data(ttl=REFRESH_SEC)
def fetch_data(symbol):

    df = yf.download(
        symbol,
        period="5d",
        interval="5m",
        progress=False
    )

    if df.empty:
        return pd.DataFrame()

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.reset_index(inplace=True)

    # Convert to IST
    df['Datetime'] = (
        pd.to_datetime(df['Datetime'], utc=True)
        .dt.tz_convert(IST)
        .dt.tz_localize(None)
    )

    df.set_index('Datetime', inplace=True)

    # If NSE instrument, restrict to market hours
    if symbol.startswith("^"):
        df = df.between_time("09:15", "15:30").copy()
    else:
        df = df.copy()

    # Forward-fill OHLC safely
    df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].ffill()

    # Drop rows where Close is still NaN
    df.dropna(subset=['Close'], inplace=True)

    if df.empty:
        return pd.DataFrame()

    # EMA
    df['EMA20'] = EMAIndicator(df['Close'], window=20, fillna=True).ema_indicator()

    # Stoch RSI
    stoch = StochRSIIndicator(df['Close'], window=14, smooth1=3, smooth2=3, fillna=True)
    df['StochRSI'] = stoch.stochrsi().squeeze()

    # Trend (computed on ascending data before sort)
    trends = ["NA"]
    for i in range(1, len(df)):
        ch = df['High'].iloc[i]
        ph = df['High'].iloc[i - 1]
        cl = df['Low'].iloc[i]
        pl = df['Low'].iloc[i - 1]

        if ch > ph and cl > pl:
            trends.append("UP")
        elif ch < ph and cl < pl:
            trends.append("DOWN")
        else:
            trends.append("Sideways")

    df['Trend'] = trends

    # Percentage-based EMA proximity threshold (0.5%)
    EMA_THRESHOLD_PCT = 0.005

    # Signal generation
    signals = []
    remarks = []

    for _, row in df.iterrows():
        close  = float(row['Close'])
        ema    = float(row['EMA20'])
        stochv = float(row['StochRSI'])
        trend  = row['Trend']

        r = []
        ema_distance_pct = abs(close - ema) / ema if ema != 0 else 1

        if ema_distance_pct > EMA_THRESHOLD_PCT:
            r.append(f"Price far from EMA20 ({ema_distance_pct * 100:.2f}%)")

        if trend == "UP" and ema_distance_pct <= EMA_THRESHOLD_PCT and stochv < 0.3:
            signals.append("CE BUY")
            base = "HH-HL + EMA near + StochRSI < 0.3"
            remarks.append(base + ("; " + "; ".join(r) if r else ""))

        elif trend == "DOWN" and ema_distance_pct <= EMA_THRESHOLD_PCT and stochv > 0.7:
            signals.append("PE BUY")
            base = "LH-LL + EMA near + StochRSI > 0.7"
            remarks.append(base + ("; " + "; ".join(r) if r else ""))

        else:
            signals.append("NO TRADE")
            remarks.append("; ".join(r) if r else "Conditions not met")

    df['Signal']  = signals
    df['Remark']  = remarks

    return df.sort_index(ascending=False)


# -------------------------------
# MAIN UI
# -------------------------------
st.title("📊 Multi Asset Live Trading Dashboard")

df = fetch_data(SYMBOL)

if df.empty:
    st.error("No data received. The market may be closed or the symbol is invalid.")
    st.stop()

latest = df.iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Instrument", selected_name)
c2.metric("Close",  round(float(latest['Close']), 2))
c3.metric("EMA20",  round(float(latest['EMA20']), 2))
c4.metric("Signal", latest['Signal'])

# Countdown placeholder
refresh_placeholder = st.empty()
st.info(f"🕒 Last Refresh (IST): {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}")
st.warning(f"📌 Remark: {latest['Remark']}")

if latest['Signal'] in ["CE BUY", "PE BUY"]:
    st.error("🚨 TRADE SIGNAL GENERATED 🚨")

st.subheader("📋 Latest Data")

all_show_cols = ['Close', 'High', 'Low', 'Open', 'Volume', 'EMA20', 'StochRSI', 'Trend', 'Signal', 'Remark']
show_cols = [c for c in all_show_cols if c in df.columns]

st.dataframe(df[show_cols], use_container_width=True, height=420)

st.download_button(
    "⬇️ Download CSV",
    data=df.to_csv().encode('utf-8'),
    file_name=f"{selected_name}_Live.csv",
    mime="text/csv"
)

# -------------------------------
# AUTO REFRESH — no external package needed
# Counts down visually, then triggers st.rerun()
# -------------------------------
for remaining in range(REFRESH_SEC, 0, -1):
    refresh_placeholder.caption(f"🔄 Refreshing in {remaining}s...")
    time.sleep(1)

refresh_placeholder.caption("🔄 Refreshing now...")
st.rerun()
