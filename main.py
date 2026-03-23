import streamlit as st
import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import StochRSIIndicator
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(page_title="Multi Asset Trading Dashboard", layout="wide")

REFRESH_SEC = 15
IST = pytz.timezone("Asia/Kolkata")

st_autorefresh(interval=REFRESH_SEC * 1000, key="refresh")

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

    # If NSE instrument, restrict time
    if symbol.startswith("^"):
        df = df.between_time("09:15", "15:30")

    df[['Open','High','Low','Close']] = df[['Open','High','Low','Close']].ffill()

    # EMA
    df['EMA20'] = EMAIndicator(df['Close'], window=20, fillna=True).ema_indicator()

    # Stoch RSI
    stoch = StochRSIIndicator(df['Close'], window=14, smooth1=3, smooth2=3, fillna=True)
    df['StochRSI'] = stoch.stochrsi()

    # Trend
    trends = ["NA"]
    for i in range(1, len(df)):
        ch, ph = df['High'].iloc[i], df['High'].iloc[i-1]
        cl, pl = df['Low'].iloc[i], df['Low'].iloc[i-1]

        if ch > ph and cl > pl:
            trends.append("UP")
        elif ch < ph and cl < pl:
            trends.append("DOWN")
        else:
            trends.append("Sideways")

    df['Trend'] = trends

    # Signal
    signals, remarks = [], []

    for _, row in df.iterrows():
        close = row['Close']
        ema = row['EMA20']
        stochv = row['StochRSI']
        trend = row['Trend']

        r = []

        if abs(close - ema) > 100:
            r.append("Price far from EMA20")

        if trend == "UP" and abs(close - ema) <= 100 and stochv < 0.3:
            signals.append("CE BUY")
            remarks.append("HH-HL + EMA near + StochRSI < 0.3")

        elif trend == "DOWN" and abs(close - ema) <= 100 and stochv > 0.7:
            signals.append("PE BUY")
            remarks.append("LH-LL + EMA near + StochRSI > 0.7")

        else:
            signals.append("NO TRADE")
            remarks.append("; ".join(r))

    df['Signal'] = signals
    df['Remark'] = remarks

    return df.sort_index(ascending=False)

# -------------------------------
# MAIN UI
# -------------------------------
st.title("📊 Multi Asset Live Trading Dashboard")

df = fetch_data(SYMBOL)

if df.empty:
    st.error("No data received")
    st.stop()

latest = df.iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Instrument", selected_name)
c2.metric("Close", round(latest['Close'],2))
c3.metric("EMA20", round(latest['EMA20'],2))
c4.metric("Signal", latest['Signal'])

st.info(
    f"🕒 Last Refresh (IST): {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}"
)

st.warning(f"📌 Remark: {latest['Remark']}")

if latest['Signal'] in ["CE BUY", "PE BUY"]:
    st.error("🚨 TRADE SIGNAL GENERATED 🚨")

st.subheader("📋 Latest Data")

show_cols = ['Close','High','Low','Open','Volume','EMA20','StochRSI','Signal','Remark']

st.dataframe(df[show_cols], use_container_width=True, height=420)

st.download_button(
    "⬇️ Download CSV",
    data=df.to_csv().encode('utf-8'),
    file_name=f"{selected_name}_Live.csv",
    mime="text/csv"
)

st.caption("🔄 Auto refresh every 15 seconds")

