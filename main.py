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
    background-color: #0a0e17 !important;
    color: #c9d1d9 !important;
    font-family: 'Rajdhani', sans-serif !important;
}

.stApp { background-color: #0a0e17 !important; }

h1, h2, h3 { color: #58a6ff !important; font-family: 'Rajdhani', sans-serif !important; font-weight: 700 !important; }

.metric-card {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 4px 0;
}

[data-testid="metric-container"] {
    background: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
}

[data-testid="metric-container"] label {
    color: #8b949e !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #e6edf3 !important;
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
    background: #0d1117;
    border: 1px solid #21262d;
    border-left: 4px solid #484f58;
    border-radius: 8px;
    padding: 16px 20px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 14px;
    color: #8b949e;
    text-align: center;
}

@keyframes pulse-green {
    0%, 100% { box-shadow: 0 0 8px #3fb95040; }
    50% { box-shadow: 0 0 24px #3fb95099; }
}

@keyframes pulse-red {
    0%, 100% { box-shadow: 0 0 8px #f8514940; }
    50% { box-shadow: 0 0 24px #f8514999; }
}

.stDataFrame {
    background: #0d1117 !important;
    border: 1px solid #21262d !important;
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

.stSidebar { background-color: #0d1117 !important; border-right: 1px solid #21262d !important; }

.stSelectbox > div, .stTextInput > div > div {
    background-color: #161b22 !important;
    border-color: #30363d !important;
    color: #e6edf3 !important;
}

.refresh-bar {
    font-family: 'Share Tech Mono', monospace;
    font-size: 12px;
    color: #8b949e;
    padding: 4px 0;
}

.sound-toggle {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 8px 0;
    font-family: 'Rajdhani', sans-serif;
    font-size: 14px;
    color: #8b949e;
}

div[data-testid="stInfo"] {
    background: #0d1f36 !important;
    border: 1px solid #1f6feb44 !important;
    border-radius: 8px !important;
    color: #79c0ff !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 12px !important;
}

div[data-testid="stWarning"] {
    background: #1c1400 !important;
    border: 1px solid #9e6a0344 !important;
    border-radius: 8px !important;
    color: #d29922 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 13px !important;
}

.stButton button {
    background: #21262d !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important;
}

.stButton button:hover {
    background: #30363d !important;
    border-color: #58a6ff !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# SOUND ALERT via Web Audio API
# -------------------------------
def play_sound_alert(signal_type):
    """Inject JS to play beep using Web Audio API — no file needed."""
    if signal_type == "CE BUY":
        # Rising two-tone beep (positive)
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
            beep(1320, 0,    0.15);
            beep(1320, 0.2, 0.15);
            beep(1320, 0.4, 0.25);
        })();
        """
    elif signal_type == "PE BUY":
        # Falling two-tone beep (alert)
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
            beep(1320, 0,    0.15);
            beep(1320, 0.2,  0.15);
            beep(1320,  0.4,  0.25);
        })();
        """
    else:
        return  # No sound for NO TRADE

    # Embed in hidden iframe so it doesn't take space
    components.html(f"""
        <script>{js_sound}</script>
    """, height=0)


# -------------------------------
# DEFAULT SYMBOL LIST
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

# Sound toggle
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

# Sound legend
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='font-size:12px; color:#8b949e; font-family: monospace; line-height:1.8'>
🔊 <b>Sound Guide</b><br>
▲ CE BUY → Rising 3-tone beep<br>
▼ PE BUY → Falling 3-tone beep<br>
<br>
⚠️ Browser must be unmuted.<br>
Click anywhere on page once<br>to activate audio context.
</div>
""", unsafe_allow_html=True)

# -------------------------------
# DATA FUNCTION
# -------------------------------
@st.cache_data(ttl=REFRESH_SEC)
def fetch_data(symbol):
    df = yf.download(symbol, period="5d", interval="5m", progress=False)

    if df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.reset_index(inplace=True)
    df['Datetime'] = (
        pd.to_datetime(df['Datetime'], utc=True)
        .dt.tz_convert(IST)
        .dt.tz_localize(None)
    )
    df.set_index('Datetime', inplace=True)

    if symbol.startswith("^"):
        df = df.between_time("09:15", "15:30").copy()
    else:
        df = df.copy()

    df[['Open','High','Low','Close']] = df[['Open','High','Low','Close']].ffill()
    df.dropna(subset=['Close'], inplace=True)

    if df.empty:
        return pd.DataFrame()

    df['EMA20']    = EMAIndicator(df['Close'], window=20, fillna=True).ema_indicator()
    stoch          = StochRSIIndicator(df['Close'], window=14, smooth1=3, smooth2=3, fillna=True)
    df['StochRSI'] = stoch.stochrsi().squeeze()

    trends = ["NA"]
    for i in range(1, len(df)):
        ch, ph = df['High'].iloc[i], df['High'].iloc[i-1]
        cl, pl = df['Low'].iloc[i],  df['Low'].iloc[i-1]
        if ch > ph and cl > pl:
            trends.append("UP")
        elif ch < ph and cl < pl:
            trends.append("DOWN")
        else:
            trends.append("Sideways")
    df['Trend'] = trends

    EMA_THRESHOLD_PCT = 0.005
    signals, remarks = [], []

    for _, row in df.iterrows():
        close  = float(row['Close'])
        ema    = float(row['EMA20'])
        stochv = float(row['StochRSI'])
        trend  = row['Trend']
        r      = []

        ema_pct = abs(close - ema) / ema if ema != 0 else 1
        if ema_pct > EMA_THRESHOLD_PCT:
            r.append(f"Price far from EMA20 ({ema_pct*100:.2f}%)")

        if trend == "UP" and ema_pct <= EMA_THRESHOLD_PCT and stochv < 0.3:
            signals.append("CE BUY")
            remarks.append("HH-HL + EMA near + StochRSI < 0.3" + ("; " + "; ".join(r) if r else ""))
        elif trend == "DOWN" and ema_pct <= EMA_THRESHOLD_PCT and stochv > 0.7:
            signals.append("PE BUY")
            remarks.append("LH-LL + EMA near + StochRSI > 0.7" + ("; " + "; ".join(r) if r else ""))
        else:
            signals.append("NO TRADE")
            remarks.append("; ".join(r) if r else "Conditions not met")

    df['Signal'] = signals
    df['Remark'] = remarks

    return df.sort_index(ascending=False)

# -------------------------------
# MAIN UI
# -------------------------------
st.markdown("# 📊 Multi Asset Trading Dashboard")
st.markdown("<div style='height:4px; background:linear-gradient(90deg,#1f6feb,#388bfd,#58a6ff20); border-radius:2px; margin-bottom:20px'></div>", unsafe_allow_html=True)

df = fetch_data(SYMBOL)

if df.empty:
    st.error("⚠️ No data received. Market may be closed or symbol invalid.")
    st.stop()

latest       = df.iloc[0]
current_sig  = latest['Signal']
current_time = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')

# --- Metrics row ---
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Instrument",  selected_name)
c2.metric("Close",       round(float(latest['Close']), 2))
c3.metric("EMA20",       round(float(latest['EMA20']), 2))
c4.metric("StochRSI",    round(float(latest['StochRSI']), 4))
c5.metric("Trend",       latest['Trend'])

st.markdown("<br>", unsafe_allow_html=True)

# --- Signal display ---
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

# --- Sound alert logic ---
# Only beep when signal CHANGES to a trade signal (avoids repeat beeping)
prev_sig = st.session_state.last_signal.get(selected_name, "")
if st.session_state.sound_enabled:
    if current_sig in ("CE BUY", "PE BUY") and current_sig != prev_sig:
        play_sound_alert(current_sig)
st.session_state.last_signal[selected_name] = current_sig

# --- Info bar ---
sound_status = "🔔 ON" if st.session_state.sound_enabled else "🔕 OFF"
st.info(f"🕒 Last Refresh (IST): {current_time}  &nbsp;|&nbsp;  Sound: {sound_status}  &nbsp;|&nbsp;  Auto-refresh every {REFRESH_SEC}s")

# --- Data table ---
st.markdown("### 📋 Latest Candles")

all_cols  = ['Close','High','Low','Open','Volume','EMA20','StochRSI','Trend','Signal','Remark']
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

# --- Auto-refresh countdown (no extra package) ---
countdown_ph = st.empty()
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
