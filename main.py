import streamlit as st
import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import StochRSIIndicator
from datetime import datetime
import pytz
import time
import streamlit.components.v1 as components

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(page_title="📊 Trading Signal Dashboard", layout="wide")

REFRESH_SEC = 15
IST = pytz.timezone("Asia/Kolkata")

# -------------------------------
# CUSTOM CSS — dark trading terminal aesthetic
# -------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    background-color: #ffffff !important;
    color: #1a1a2e !important;
    font-family: 'Rajdhani', sans-serif !important;
}

.stApp { background-color: #ffffff !important; }

h1, h2, h3 { color: #1f6feb !important; font-family: 'Rajdhani', sans-serif !important; font-weight: 700 !important; }

[data-testid="metric-container"] {
    background: #f6f8fa !important;
    border: 1px solid #d0d7de !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
}
[data-testid="metric-container"] label {
    color: #57606a !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #1a1a2e !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 22px !important;
}

.signal-ce {
    background: linear-gradient(135deg, #0d2818, #0f3a1f);
    border: 1px solid #238636;
    border-left: 4px solid #3fb950;
    border-radius: 8px;
    padding: 16px 20px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 18px;
    color: #3fb950;
    font-weight: bold;
    text-align: center;
    animation: pulse-green 1.5s infinite;
}
.signal-pe {
    background: linear-gradient(135deg, #2d0a0a, #3a0f0f);
    border: 1px solid #da3633;
    border-left: 4px solid #f85149;
    border-radius: 8px;
    padding: 16px 20px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 18px;
    color: #f85149;
    font-weight: bold;
    text-align: center;
    animation: pulse-red 1.5s infinite;
}
.signal-none {
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-left: 4px solid #8c959f;
    border-radius: 8px;
    padding: 16px 20px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 14px;
    color: #57606a;
    text-align: center;
}

@keyframes pulse-green {
    0%, 100% { box-shadow: 0 0 8px #3fb95040; }
    50%       { box-shadow: 0 0 24px #3fb95099; }
}
@keyframes pulse-red {
    0%, 100% { box-shadow: 0 0 8px #f8514940; }
    50%       { box-shadow: 0 0 24px #f8514999; }
}

.stDataFrame {
    background: #f6f8fa !important;
    border: 1px solid #d0d7de !important;
    border-radius: 8px !important;
}
.stDownloadButton button {
    background: #1f6feb !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important;
}
.stSidebar { background-color: #f6f8fa !important; border-right: 1px solid #d0d7de !important; }
.stSelectbox > div, .stTextInput > div > div {
    background-color: #ffffff !important;
    border-color: #d0d7de !important;
    color: #1a1a2e !important;
}
.refresh-bar {
    font-family: 'Share Tech Mono', monospace;
    font-size: 12px;
    color: #57606a;
    padding: 4px 0;
}
div[data-testid="stInfo"] {
    background: #ddf4ff !important;
    border: 1px solid #54aeff44 !important;
    border-radius: 8px !important;
    color: #0550ae !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 12px !important;
}
.stButton button {
    background: #f6f8fa !important;
    color: #1a1a2e !important;
    border: 1px solid #d0d7de !important;
    border-radius: 6px !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important;
}
.stButton button:hover {
    background: #e8f0fe !important;
    border-color: #1f6feb !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# SOUND ALERT via Web Audio API
# -------------------------------
def play_sound_alert(signal_type):
    if signal_type == "CE BUY":
        js_sound = """
        (function() {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            function beep(freq, start, dur, vol=0.4) {
                const o = ctx.createOscillator();
                const g = ctx.createGain();
                o.connect(g); g.connect(ctx.destination);
                o.type = 'sine';
                o.frequency.setValueAtTime(freq, ctx.currentTime + start);
                g.gain.setValueAtTime(0, ctx.currentTime + start);
                g.gain.linearRampToValueAtTime(vol, ctx.currentTime + start + 0.02);
                g.gain.linearRampToValueAtTime(0, ctx.currentTime + start + dur);
                o.start(ctx.currentTime + start);
                o.stop(ctx.currentTime + start + dur + 0.05);
            }
            beep(880,  0,   0.15);
            beep(1100, 0.2, 0.15);
            beep(1320, 0.4, 0.25);
        })();
        """
    elif signal_type == "PE BUY":
        js_sound = """
        (function() {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            function beep(freq, start, dur, vol=0.4) {
                const o = ctx.createOscillator();
                const g = ctx.createGain();
                o.connect(g); g.connect(ctx.destination);
                o.type = 'sine';
                o.frequency.setValueAtTime(freq, ctx.currentTime + start);
                g.gain.setValueAtTime(0, ctx.currentTime + start);
                g.gain.linearRampToValueAtTime(vol, ctx.currentTime + start + 0.02);
                g.gain.linearRampToValueAtTime(0, ctx.currentTime + start + dur);
                o.start(ctx.currentTime + start);
                o.stop(ctx.currentTime + start + dur + 0.05);
            }
            beep(1320, 0,   0.15);
            beep(1100, 0.2, 0.15);
            beep(880,  0.4, 0.25);
        })();
        """
    else:
        return

    components.html(f"<script>{js_sound}</script>", height=0)


# -------------------------------
# SESSION STATE
# -------------------------------
if "symbols" not in st.session_state:
    st.session_state.symbols = {
        "Bank Nifty": "^NSEBANK",
        "Nifty 50":   "^NSEI",
        "Bitcoin":    "BTC-USD",
        "Ethereum":   "ETH-USD"
    }

if "last_signal" not in st.session_state:
    st.session_state.last_signal = {}

if "sound_enabled" not in st.session_state:
    st.session_state.sound_enabled = True

# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.markdown("## 📌 Instrument")

selected_name = st.sidebar.selectbox(
    "Choose Symbol",
    list(st.session_state.symbols.keys())
)
SYMBOL = st.session_state.symbols[selected_name]

st.sidebar.markdown("---")

sound_label = "🔔 Sound ON" if st.session_state.sound_enabled else "🔕 Sound OFF"
if st.sidebar.button(sound_label):
    st.session_state.sound_enabled = not st.session_state.sound_enabled
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ➕ Add Symbol")
new_name   = st.sidebar.text_input("Display Name")
new_symbol = st.sidebar.text_input("Yahoo Symbol (e.g. SOL-USD)")
if st.sidebar.button("Add Symbol"):
    if new_name and new_symbol:
        st.session_state.symbols[new_name] = new_symbol.upper()
        st.sidebar.success("✅ Added")

st.sidebar.markdown("### ➖ Remove Symbol")
remove_name = st.sidebar.selectbox("Select to Remove", list(st.session_state.symbols.keys()))
if st.sidebar.button("Remove Symbol"):
    if len(st.session_state.symbols) > 1:
        del st.session_state.symbols[remove_name]
        st.sidebar.success("✅ Removed")
    else:
        st.sidebar.warning("Need at least one symbol")

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='font-size:12px; color:#8b949e; font-family: monospace; line-height:1.8'>
🔊 <b>Sound Guide</b><br>
▲ CE BUY → Rising 3-tone beep<br>
▼ PE BUY → Falling 3-tone beep<br>
<br>
⚠️ Click page once to activate audio.<br>
Ensure browser tab is not muted.
</div>
""", unsafe_allow_html=True)


# -------------------------------
# DATA FUNCTION — signal logic exactly matches tkinter working code
# -------------------------------
@st.cache_data(ttl=REFRESH_SEC)
def fetch_data(symbol):

    # FIX 1: auto_adjust=False — matches your tkinter code exactly
    df = yf.download(
        symbol,
        period="5d",
        interval="5m",
        auto_adjust=False,
        progress=False
    )

    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.reset_index(inplace=True)

    # FIX 2: UTC→IST via simple Timedelta offset — matches your tkinter code exactly
    df['Datetime'] = pd.to_datetime(df['Datetime']) + pd.Timedelta(hours=5, minutes=30)
    df.set_index('Datetime', inplace=True)

    # NSE market hours filter
    if symbol.startswith("^"):
        df = df.between_time("09:15", "15:30").copy()
    else:
        df = df.copy()

    # Clean numeric columns
    for col in ['Open', 'High', 'Low', 'Close', 'Adj Close']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].ffill()
    df.dropna(subset=['Close'], inplace=True)

    if df.empty:
        return pd.DataFrame()

    # EMA 20
    df['EMA20'] = EMAIndicator(close=df['Close'], window=20, fillna=True).ema_indicator()

    # Stochastic RSI
    stoch = StochRSIIndicator(
        close=df['Close'],
        window=14,
        smooth1=3,
        smooth2=3,
        fillna=True
    )
    df['StochRSI'] = stoch.stochrsi().squeeze()

    # ---- Trend Logic: HH-HL = UP, LH-LL = DOWN ----
    trends = ["NA"]
    for i in range(1, len(df)):
        ch, ph = df['High'].iloc[i], df['High'].iloc[i - 1]
        cl, pl = df['Low'].iloc[i],  df['Low'].iloc[i - 1]
        if ch > ph and cl > pl:
            trends.append("UP")
        elif ch < ph and cl < pl:
            trends.append("DOWN")
        else:
            trends.append("Sideways")
    df['Trend'] = trends

    # ---- Signal Logic — FIX 3: Exact match to tkinter code ----
    # Uses abs(close - ema20) > 100 (hardcoded 100 pts, NOT percentage-based)
    signals, remarks = [], []

    for _, row in df.iterrows():
        trend  = row['Trend']
        close  = float(row['Close'])
        ema20  = float(row['EMA20'])
        stochv = float(row['StochRSI'])

        remark = []

        if abs(close - ema20) > 100:
            remark.append("Price far from EMA20")

        if trend == "UP" and abs(close - ema20) <= 100 and stochv < 0.3:
            signals.append("CE BUY")
            remarks.append("HH-HL trend + EMA near + StochRSI < 0.3")

        elif trend == "DOWN" and abs(close - ema20) <= 100 and stochv > 0.7:
            signals.append("PE BUY")
            remarks.append("LH-LL trend + EMA near + StochRSI > 0.7")

        else:
            # FIX 4: Detailed NO TRADE remarks — exactly matches tkinter code
            if trend == "Sideways":
                remark.append("Market sideways")
            if trend == "UP" and stochv >= 0.3:
                remark.append("StochRSI not low enough for CE")
            if trend == "DOWN" and stochv <= 0.7:
                remark.append("StochRSI not high enough for PE")

            signals.append("NO TRADE")
            remarks.append("; ".join(remark))

    df['Signal'] = signals
    df['Remark'] = remarks

    # FIX 5: Show latest trading day only — matches tkinter code
    latest_day = df.index.date.max()
    df = df[df.index.date == latest_day]

    # Round display values
    for col in ['Adj Close', 'Close', 'High', 'Low', 'Open', 'EMA20']:
        if col in df.columns:
            df[col] = df[col].round(2)

    return df.sort_index(ascending=False)


# -------------------------------
# MAIN UI
# -------------------------------
st.markdown("# 📊 Multi Asset Trading Dashboard")
st.markdown(
    "<div style='height:4px; background:linear-gradient(90deg,#1f6feb,#388bfd,#58a6ff20);"
    "border-radius:2px; margin-bottom:20px'></div>",
    unsafe_allow_html=True
)

df = fetch_data(SYMBOL)

if df.empty:
    st.error("⚠️ No data received. Market may be closed or symbol invalid.")
    st.stop()

latest      = df.iloc[0]
current_sig = latest['Signal']
now_ist     = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')

# --- Metrics row ---
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Instrument", selected_name)
c2.metric("Close",      round(float(latest['Close']), 2))
c3.metric("EMA20",      round(float(latest['EMA20']), 2))
c4.metric("StochRSI",   round(float(latest['StochRSI']), 4))
c5.metric("Trend",      latest['Trend'])

st.markdown("<br>", unsafe_allow_html=True)

# --- Signal banner ---
if current_sig == "CE BUY":
    st.markdown(f"""
    <div class="signal-ce">
        🟢 &nbsp;&nbsp; CE BUY SIGNAL &nbsp;&nbsp; 🟢<br>
        <span style='font-size:13px; font-weight:400; color:#8ee2a0'>{latest['Remark']}</span>
    </div>
    """, unsafe_allow_html=True)
elif current_sig == "PE BUY":
    st.markdown(f"""
    <div class="signal-pe">
        🔴 &nbsp;&nbsp; PE BUY SIGNAL &nbsp;&nbsp; 🔴<br>
        <span style='font-size:13px; font-weight:400; color:#ffaaaa'>{latest['Remark']}</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="signal-none">
        ⬜ &nbsp; NO TRADE &nbsp; — &nbsp; {latest['Remark']}
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Sound alert: beep only when signal changes to a trade signal ---
prev_sig = st.session_state.last_signal.get(selected_name, "")
if st.session_state.sound_enabled:
    if current_sig in ("CE BUY", "PE BUY") and current_sig != prev_sig:
        play_sound_alert(current_sig)
# Reset last_signal when back to NO TRADE (so next signal fires again)
if current_sig == "NO TRADE":
    st.session_state.last_signal[selected_name] = ""
else:
    st.session_state.last_signal[selected_name] = current_sig

# --- Status bar with inline countdown ---
sound_status = "🔔 ON" if st.session_state.sound_enabled else "🔕 OFF"
countdown_ph = st.empty()  # placeholder sits right here, next to status info

st.info(
    f"🕒 Last Refresh (IST): {now_ist}  &nbsp;|&nbsp;  "
    f"Sound: {sound_status}  &nbsp;|&nbsp;  "
    f"Auto-refresh every {REFRESH_SEC}s"
)

# --- Data table ---
st.markdown("### 📋 Today's Candles")

all_cols  = ['Close', 'High', 'Low', 'Open', 'Volume', 'EMA20', 'StochRSI', 'Trend', 'Signal', 'Remark']
show_cols = [c for c in all_cols if c in df.columns]

st.dataframe(
    df[show_cols].style.apply(
        lambda col: [
            'background-color: #0d2818; color: #3fb950' if v == 'CE BUY'
            else 'background-color: #2d0a0a; color: #f85149' if v == 'PE BUY'
            else '' for v in col
        ] if col.name == 'Signal' else ['' for _ in col],
        axis=0
    ),
    use_container_width=True,
    height=400
)

st.download_button(
    "⬇️ Download CSV",
    data=df.to_csv().encode('utf-8'),
    file_name=f"{selected_name}_signals.csv",
    mime="text/csv"
)

# --- Countdown runs here but displays ABOVE the table (placeholder set earlier) ---
for remaining in range(REFRESH_SEC, 0, -1):
    countdown_ph.markdown(
        f"<div class='refresh-bar'>🔄 Next refresh in {remaining}s...</div>",
        unsafe_allow_html=True
    )
    time.sleep(1)

countdown_ph.markdown(
    "<div class='refresh-bar'>🔄 Refreshing...</div>",
    unsafe_allow_html=True
)
st.rerun()
