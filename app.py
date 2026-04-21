import streamlit as st
import pandas as pd
import time
from datetime import datetime
import pytz
from scanner import scan_breakouts

st.set_page_config(
    page_title="Nifty 500 Breakout Scanner",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.main-title { font-size: 2rem; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 0; }
.subtitle { color: #888; font-size: 0.95rem; margin-top: 0.2rem; }
.stProgress > div > div > div { background-color: #fd7e14; }
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
.market-open  { background:#d1fae5; color:#065f46; padding:4px 12px; border-radius:6px; font-size:0.85rem; font-weight:600; display:inline-block; }
.market-closed{ background:#fee2e2; color:#991b1b; padding:4px 12px; border-radius:6px; font-size:0.85rem; font-weight:600; display:inline-block; }
</style>
""", unsafe_allow_html=True)

REFRESH_INTERVAL = 30 * 60  # 30 minutes in seconds
IST = pytz.timezone("Asia/Kolkata")

# ── Market hours helpers ──────────────────────────────────────────────────────
def ist_now():
    return datetime.now(IST)

def is_market_open():
    now = ist_now()
    if now.weekday() >= 5:          # Saturday=5, Sunday=6
        return False
    market_open  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close

def market_status_text():
    now = ist_now()
    if now.weekday() >= 5:
        days_until_monday = 7 - now.weekday()
        return "closed", f"Weekend — opens Monday 9:15 AM IST"
    market_open  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now < market_open:
        delta = market_open - now
        mins  = int(delta.total_seconds() // 60)
        return "closed", f"Pre-market — opens in {mins} min (9:15 AM IST)"
    if now > market_close:
        return "closed", f"Market closed at 3:30 PM IST · Showing last scan"
    # Market is open — show time remaining
    delta = market_close - now
    mins  = int(delta.total_seconds() // 60)
    return "open", f"Market open · Closes in {mins} min (3:30 PM IST)"

# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.markdown('<p class="main-title">🔥 Nifty 500 Breakout Scanner</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Triple-confirmed breakouts: Price × Volume × Trend</p>', unsafe_allow_html=True)
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    manual_refresh = st.button("↻ Refresh Now", use_container_width=True, type="primary")

# ── Market status badge ───────────────────────────────────────────────────────
status_type, status_msg = market_status_text()
badge_class = "market-open" if status_type == "open" else "market-closed"
icon = "🟢" if status_type == "open" else "🔴"
st.markdown(f'<span class="{badge_class}">{icon} {status_msg}</span>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "last_scan_time"  not in st.session_state: st.session_state.last_scan_time  = 0
if "results"         not in st.session_state: st.session_state.results         = None
if "errors"          not in st.session_state: st.session_state.errors          = []
if "scan_timestamp"  not in st.session_state: st.session_state.scan_timestamp  = None

now_ts = time.time()
time_since_last = now_ts - st.session_state.last_scan_time
due_for_refresh = time_since_last >= REFRESH_INTERVAL

# Only auto-scan if market is open (or manual override)
needs_scan = (
    manual_refresh
    or (st.session_state.results is None and is_market_open())
    or (due_for_refresh and is_market_open())
)

# First load outside market hours — show last results or a message, don't scan
first_load_closed = st.session_state.results is None and not is_market_open() and not manual_refresh

# ── Scan ──────────────────────────────────────────────────────────────────────
if needs_scan:
    st.markdown("---")
    st.markdown("**Scanning all 500 stocks...** Takes ~3 minutes.")
    bar    = st.progress(0)
    status = st.empty()

    def on_progress(cur, total, ticker):
        bar.progress(cur / total)
        status.markdown(f"⏳ `{ticker}` &nbsp;—&nbsp; {cur}/{total} &nbsp;({int(cur/total*100)}%)")

    results, errors, ts = scan_breakouts(progress_callback=on_progress)
    bar.empty(); status.empty()

    st.session_state.results        = results
    st.session_state.errors         = errors
    st.session_state.last_scan_time = time.time()
    st.session_state.scan_timestamp = ts

# ── Outside market hours, no data yet ────────────────────────────────────────
if first_load_closed:
    st.markdown("---")
    st.info(
        "📴 **Market is currently closed.** Auto-scan is paused.\n\n"
        "Results from the last session will appear here once you open the app during market hours (Mon–Fri, 9:15 AM – 3:30 PM IST). "
        "You can also hit **↻ Refresh Now** to run a manual scan anytime."
    )

# ── Display results ───────────────────────────────────────────────────────────
results = st.session_state.results
scan_ts = st.session_state.scan_timestamp

if results is not None:
    st.markdown("---")

    time_since = time.time() - st.session_state.last_scan_time
    next_min   = max(0, int((REFRESH_INTERVAL - time_since) / 60))
    ts_str     = scan_ts.strftime("%d %b %Y, %I:%M %p IST") if scan_ts else "—"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔥 Breakouts Found", len(results))
    m2.metric("📊 Universe", "Nifty 500")
    if is_market_open():
        m3.metric("⏱ Next Refresh", f"{next_min} min")
    else:
        m3.metric("⏱ Auto-Refresh", "Paused (market closed)")
    m4.metric("🕐 Last Scanned", ts_str)

    st.markdown("---")

    if len(results) == 0:
        st.info("""
**No breakouts right now — and that's a valid signal.**

All 500 stocks are either trading below their 20-day highs, or showing below-average volume, or both.
This is normal during consolidation phases. On a strong trending day you'll typically see 5–30 breakouts.
        """)
    else:
        st.markdown(f"### {len(results)} Breakout Stock{'s' if len(results) != 1 else ''}")
        st.caption("Sorted by Volume Ratio — strongest conviction first. All 3 conditions: Close > 20D High | Volume > 1.5× avg | Close > 20D MA")

        df_display = pd.DataFrame(results).drop(columns=["_ticker_full"])

        def style_df(df):
            styled = df.style.format({
                "Close (₹)":        "₹{:.2f}",
                "20D High (₹)":     "₹{:.2f}",
                "20D MA (₹)":       "₹{:.2f}",
                "% Above 20D High": "{:+.2f}%",
                "Day Change (%)":   "{:+.2f}%",
                "Volume Ratio":     "{:.2f}×",
            })
            styled = styled.applymap(
                lambda v: "color:#198754;font-weight:600" if v > 0 else "color:#dc3545;font-weight:600",
                subset=["Day Change (%)", "% Above 20D High"]
            )
            styled = styled.applymap(
                lambda v: "color:#fd7e14;font-weight:600",
                subset=["Volume Ratio"]
            )
            return styled

        st.dataframe(
            style_df(df_display),
            use_container_width=True,
            hide_index=True,
            height=min(600, 50 + len(df_display) * 38),
        )

        csv = df_display.to_csv(index=False)
        st.download_button(
            label="⬇ Download CSV",
            data=csv,
            file_name=f"breakouts_{scan_ts.strftime('%Y%m%d_%H%M') if scan_ts else 'today'}.csv",
            mime="text/csv",
        )

    if st.session_state.errors:
        with st.expander(f"⚠️ {len(st.session_state.errors)} tickers skipped"):
            for e in st.session_state.errors[:20]:
                st.caption(f"`{e['ticker']}` — {e['error']}")

# ── Methodology ───────────────────────────────────────────────────────────────
with st.expander("📖 How the breakout logic works"):
    st.markdown("""
**All 3 conditions must be true simultaneously:**

| Condition | What it checks | Why it matters |
|---|---|---|
| `Close > 20-Day High` | Price broke above 20-day rolling resistance | The actual breakout |
| `Volume > 1.5× 10-Day Avg` | Unusual buying surge vs recent baseline | Confirms real demand, not a fake-out |
| `Close > 20-Day MA` | Stock is in an uptrend | Filters stocks in downtrends |

**Auto-refresh:** Every 30 minutes, but **only during NSE market hours** (Mon–Fri, 9:15 AM – 3:30 PM IST).  
Outside market hours the scanner pauses — no point refreshing stale data.
    """)

# ── Auto-rerun logic ──────────────────────────────────────────────────────────
if is_market_open():
    # Market is open — sleep up to 60s then recheck
    elapsed   = time.time() - st.session_state.last_scan_time
    remaining = REFRESH_INTERVAL - elapsed
    if remaining > 0:
        mins = int(remaining // 60)
        secs = int(remaining % 60)
        st.caption(f"🔄 Next auto-scan in {mins}m {secs}s")
        time.sleep(min(remaining, 60))
        st.rerun()
else:
    # Market closed — just show current IST time, no rerun loop
    st.caption(f"🕐 Current IST time: {ist_now().strftime('%d %b %Y, %I:%M %p')}")




















# import streamlit as st
# import pandas as pd
# import time
# from scanner import scan_breakouts

# st.set_page_config(
#     page_title="Nifty 500 Breakout Scanner",
#     page_icon="🔥",
#     layout="wide",
#     initial_sidebar_state="collapsed",
# )

# st.markdown("""
# <style>
# .main-title { font-size: 2rem; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 0; }
# .subtitle { color: #888; font-size: 0.95rem; margin-top: 0.2rem; }
# .stProgress > div > div > div { background-color: #fd7e14; }
# div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
# </style>
# """, unsafe_allow_html=True)

# REFRESH_INTERVAL = 30 * 60  # 30 minutes

# # ── Header ────────────────────────────────────────────────────────────────────
# col_title, col_btn = st.columns([3, 1])
# with col_title:
#     st.markdown('<p class="main-title">🔥 Nifty 500 Breakout Scanner</p>', unsafe_allow_html=True)
#     st.markdown('<p class="subtitle">Triple-confirmed breakouts: Price × Volume × Trend · Auto-refreshes every 30 min</p>', unsafe_allow_html=True)
# with col_btn:
#     st.markdown("<br>", unsafe_allow_html=True)
#     manual_refresh = st.button("↻ Refresh Now", use_container_width=True, type="primary")

# # ── Session state ─────────────────────────────────────────────────────────────
# if "last_scan_time"   not in st.session_state: st.session_state.last_scan_time   = 0
# if "results"          not in st.session_state: st.session_state.results          = None
# if "errors"           not in st.session_state: st.session_state.errors           = []
# if "scan_timestamp"   not in st.session_state: st.session_state.scan_timestamp   = None
# if "market_snapshot"  not in st.session_state: st.session_state.market_snapshot  = {}

# now = time.time()
# needs_refresh = (
#     st.session_state.results is None
#     or (now - st.session_state.last_scan_time) >= REFRESH_INTERVAL
#     or manual_refresh
# )

# # ── Scan ──────────────────────────────────────────────────────────────────────
# if needs_refresh:
#     st.markdown("---")
#     st.markdown("**Scanning all 500 stocks...** Takes ~3 minutes. Grab a chai ☕")
#     bar = st.progress(0)
#     status = st.empty()

#     def on_progress(cur, total, ticker):
#         bar.progress(cur / total)
#         status.markdown(f"⏳ `{ticker}` &nbsp;—&nbsp; {cur}/{total} &nbsp;({int(cur/total*100)}%)")

#     results, errors, ts = scan_breakouts(progress_callback=on_progress)

#     # Save a quick market snapshot (% stocks above 20DMA) for context
#     bar.empty(); status.empty()

#     st.session_state.results         = results
#     st.session_state.errors          = errors
#     st.session_state.last_scan_time  = time.time()
#     st.session_state.scan_timestamp  = ts

# # ── Display ───────────────────────────────────────────────────────────────────
# results = st.session_state.results
# scan_ts = st.session_state.scan_timestamp

# if results is not None:
#     st.markdown("---")

#     time_since = time.time() - st.session_state.last_scan_time
#     next_min   = max(0, int((REFRESH_INTERVAL - time_since) / 60))
#     ts_str     = scan_ts.strftime("%d %b %Y, %I:%M %p") if scan_ts else "—"

#     m1, m2, m3, m4 = st.columns(4)
#     m1.metric("🔥 Breakouts Found", len(results))
#     m2.metric("📊 Universe", "Nifty 500")
#     m3.metric("⏱ Next Refresh", f"{next_min} min")
#     m4.metric("🕐 Last Scanned", ts_str)

#     st.markdown("---")

#     if len(results) == 0:
#         st.info("""
# **No breakouts right now — and that's a valid signal.**

# Based on the last scan, all 500 stocks are either:
# - Trading **below** their 20-day highs (market in pullback), or
# - Showing **below-average volume** (no institutional conviction), or both

# This is completely normal during consolidation phases. The scanner will catch the next move when it comes.
#         """)
#         st.markdown("**What to expect:** On an active trending day, you'll typically see 5–30 breakouts across Nifty 500. On a strong breakout day (like a broad rally), you might see 50+.")

#     else:
#         st.markdown(f"### {len(results)} Breakout Stock{'s' if len(results) != 1 else ''}")
#         st.caption("Sorted by Volume Ratio — strongest institutional conviction first. All 3 conditions confirmed: Close > 20D High | Volume > 1.5× avg | Close > 20D MA")

#         df_display = pd.DataFrame(results).drop(columns=["_ticker_full"])

#         def style_df(df):
#             styled = df.style.format({
#                 "Close (₹)":        "₹{:.2f}",
#                 "20D High (₹)":     "₹{:.2f}",
#                 "20D MA (₹)":       "₹{:.2f}",
#                 "% Above 20D High": "{:+.2f}%",
#                 "Day Change (%)":   "{:+.2f}%",
#                 "Volume Ratio":     "{:.2f}×",
#             })
#             styled = styled.applymap(
#                 lambda v: "color: #198754; font-weight:600" if v > 0 else "color: #dc3545; font-weight:600",
#                 subset=["Day Change (%)", "% Above 20D High"]
#             )
#             styled = styled.applymap(
#                 lambda v: "color: #fd7e14; font-weight:600",
#                 subset=["Volume Ratio"]
#             )
#             return styled

#         st.dataframe(
#             style_df(df_display),
#             use_container_width=True,
#             hide_index=True,
#             height=min(600, 50 + len(df_display) * 38),
#         )

#         csv = df_display.to_csv(index=False)
#         st.download_button(
#             label="⬇ Download CSV",
#             data=csv,
#             file_name=f"breakouts_{scan_ts.strftime('%Y%m%d_%H%M') if scan_ts else 'today'}.csv",
#             mime="text/csv",
#         )

#     # ── Errors ──
#     if st.session_state.errors:
#         with st.expander(f"⚠️ {len(st.session_state.errors)} tickers skipped"):
#             for e in st.session_state.errors[:20]:
#                 st.caption(f"`{e['ticker']}` — {e['error']}")

# # ── Methodology ───────────────────────────────────────────────────────────────
# with st.expander("📖 How the breakout logic works"):
#     st.markdown("""
# **All 3 conditions must be true simultaneously:**

# | Condition | What it checks | Why it matters |
# |---|---|---|
# | `Close > 20-Day High` | Price broke above 20-day rolling resistance | The actual breakout |
# | `Volume > 1.5× 10-Day Avg` | Unusual buying surge vs recent baseline | Confirms real demand, not a fake-out |
# | `Close > 20-Day MA` | Stock is in an uptrend | Filters stocks in downtrends |

# **Sorted by Volume Ratio** — a 3× volume breakout is stronger than a 1.6× one.

# **Data:** Yahoo Finance (NSE daily OHLCV), 3-month lookback, auto-refreshes every 30 minutes.
#     """)

# # ── Auto-rerun ────────────────────────────────────────────────────────────────
# if st.session_state.results is not None:
#     elapsed   = time.time() - st.session_state.last_scan_time
#     remaining = REFRESH_INTERVAL - elapsed
#     if remaining > 0:
#         mins = int(remaining // 60)
#         secs = int(remaining % 60)
#         st.caption(f"🔄 Auto-refreshing in {mins}m {secs}s")
#         time.sleep(min(remaining, 60))
#         st.rerun()











# import streamlit as st
# import yfinance as yf
# import pandas as pd

# st.set_page_config(page_title="Breakout Debug", layout="wide")
# st.title("🔍 Breakout Scanner — Debug Mode")

# # Test with just 10 well-known stocks first
# TEST_STOCKS = [
#     "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
#     "LT.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS"
# ]

# st.markdown("Testing 10 stocks with **relaxed conditions** to verify data is flowing correctly.")
# st.markdown("---")

# rows = []
# progress = st.progress(0)
# status = st.empty()

# for i, ticker in enumerate(TEST_STOCKS):
#     progress.progress((i + 1) / len(TEST_STOCKS))
#     status.text(f"Fetching {ticker}...")

#     try:
#         df = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)

#         if isinstance(df.columns, pd.MultiIndex):
#             df.columns = df.columns.get_level_values(0)

#         if df.empty or len(df) < 21:
#             rows.append({"Ticker": ticker, "C > 20H": "no data", "V > 1.5x": "no data", "C > 20DMA": "no data"})
#             continue

#         df["20DMA"]    = df["Close"].rolling(20).mean()
#         df["10VolAvg"] = df["Volume"].rolling(10).mean()
#         df["20High"]   = df["High"].rolling(20).max()

#         latest = df.iloc[-1]
#         close  = float(latest["Close"])
#         high20 = float(latest["20High"])
#         vol    = float(latest["Volume"])
#         volavg = float(latest["10VolAvg"])
#         dma20  = float(latest["20DMA"])

#         c1 = close > high20
#         c2 = vol > 1.5 * volavg
#         c3 = close > dma20

#         rows.append({
#             "Ticker":          ticker.replace(".NS", ""),
#             "Close ₹":         round(close, 1),
#             "20D High ₹":      round(high20, 1),
#             "Vol Ratio":       round(vol / volavg, 2),
#             "20D MA ₹":        round(dma20, 1),
#             "C > 20H":         "✅" if c1 else "❌",
#             "V > 1.5×avg":     "✅" if c2 else "❌",
#             "C > 20DMA":       "✅" if c3 else "❌",
#             "Strict (all 3)":  "🔥" if (c1 and c2 and c3) else "—",
#             "Relaxed (any 1)": "⚡" if (c1 or c2 or c3) else "—",
#         })

#     except Exception as e:
#         rows.append({"Ticker": ticker, "Error": str(e)})

# progress.empty()
# status.empty()

# st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# st.markdown("---")
# st.markdown("""
# **How to read this:**
# - `C > 20H` — Close broke above 20-day rolling high
# - `V > 1.5×avg` — Volume surge (50%+ above 10-day avg)
# - `C > 20DMA` — Close above 20-day moving average (uptrend)
# - **Strict** = all 3 true → original scanner logic
# - **Relaxed** = any 1 true → you should see several stocks here

# If **Relaxed** is also all `—`, the data pipeline has a problem. Share a screenshot and I'll fix it.
# """)















# import streamlit as st
# import pandas as pd
# import time
# from scanner import scan_breakouts

# # ── Page config ──────────────────────────────────────────────────────────────
# st.set_page_config(
#     page_title="Nifty 500 Breakout Scanner",
#     page_icon="🔥",
#     layout="wide",
#     initial_sidebar_state="collapsed",
# )

# # ── Styles ────────────────────────────────────────────────────────────────────
# st.markdown("""
# <style>
#     .main-title {
#         font-size: 2rem;
#         font-weight: 700;
#         letter-spacing: -0.5px;
#         margin-bottom: 0;
#     }
#     .subtitle {
#         color: #888;
#         font-size: 0.95rem;
#         margin-top: 0.2rem;
#     }
#     .metric-card {
#         background: #f8f9fa;
#         border-radius: 12px;
#         padding: 16px 20px;
#         border: 1px solid #e9ecef;
#     }
#     .breakout-tag {
#         background: #fff3cd;
#         color: #856404;
#         padding: 2px 8px;
#         border-radius: 6px;
#         font-size: 0.75rem;
#         font-weight: 600;
#     }
#     .positive { color: #198754; font-weight: 600; }
#     .negative { color: #dc3545; font-weight: 600; }
#     div[data-testid="stDataFrame"] {
#         border-radius: 10px;
#         overflow: hidden;
#     }
#     .stProgress > div > div > div {
#         background-color: #fd7e14;
#     }
# </style>
# """, unsafe_allow_html=True)

# REFRESH_INTERVAL = 30 * 60  # 30 minutes in seconds

# # ── Header ────────────────────────────────────────────────────────────────────
# col_title, col_refresh = st.columns([3, 1])
# with col_title:
#     st.markdown('<p class="main-title">🔥 Nifty 500 Breakout Scanner</p>', unsafe_allow_html=True)
#     st.markdown('<p class="subtitle">Triple-confirmed breakouts: Price × Volume × Trend</p>', unsafe_allow_html=True)

# with col_refresh:
#     st.markdown("<br>", unsafe_allow_html=True)
#     manual_refresh = st.button("↻ Refresh Now", use_container_width=True, type="primary")

# # ── Session state init ────────────────────────────────────────────────────────
# if "last_scan_time" not in st.session_state:
#     st.session_state.last_scan_time = 0
# if "results" not in st.session_state:
#     st.session_state.results = None
# if "errors" not in st.session_state:
#     st.session_state.errors = []
# if "scan_timestamp" not in st.session_state:
#     st.session_state.scan_timestamp = None

# # ── Auto-refresh logic ────────────────────────────────────────────────────────
# now = time.time()
# time_since_last = now - st.session_state.last_scan_time
# needs_refresh = (
#     st.session_state.results is None
#     or time_since_last >= REFRESH_INTERVAL
#     or manual_refresh
# )

# # ── Scan ──────────────────────────────────────────────────────────────────────
# if needs_refresh:
#     st.markdown("---")
#     st.markdown("**Scanning Nifty 500...** This takes ~2–3 minutes on first load.")

#     progress_bar = st.progress(0)
#     status_text = st.empty()

#     def update_progress(current, total, ticker):
#         pct = current / total
#         progress_bar.progress(pct)
#         status_text.markdown(
#             f"⏳ `{ticker}` — {current}/{total} stocks scanned "
#             f"({int(pct * 100)}%)"
#         )

#     results, errors, ts = scan_breakouts(progress_callback=update_progress)

#     progress_bar.empty()
#     status_text.empty()

#     st.session_state.results = results
#     st.session_state.errors = errors
#     st.session_state.last_scan_time = time.time()
#     st.session_state.scan_timestamp = ts

# # ── Display results ───────────────────────────────────────────────────────────
# results = st.session_state.results
# scan_ts = st.session_state.scan_timestamp

# if results is not None:
#     # ── Summary metrics ──
#     st.markdown("---")
#     m1, m2, m3, m4 = st.columns(4)

#     with m1:
#         st.metric("🔥 Breakouts Found", len(results))
#     with m2:
#         st.metric("📊 Stocks Scanned", 500)
#     with m3:
#         next_refresh_mins = max(0, int((REFRESH_INTERVAL - time_since_last) / 60))
#         st.metric("⏱ Next Refresh", f"{next_refresh_mins} min")
#     with m4:
#         ts_str = scan_ts.strftime("%d %b %Y, %I:%M %p") if scan_ts else "—"
#         st.metric("🕐 Last Scanned", ts_str)

#     st.markdown("---")

#     if len(results) == 0:
#         st.info(
#             "✅ No breakouts detected right now. "
#             "The market may be in a consolidation phase, or this scan ran outside market hours."
#         )
#     else:
#         st.markdown(f"### {len(results)} Breakout Stock{'s' if len(results) != 1 else ''} Today")
#         st.caption(
#             "Sorted by Volume Ratio (strongest institutional volume first). "
#             "All 3 conditions must be true: Close > 20D High | Volume > 1.5× avg | Close > 20D MA"
#         )

#         # Build dataframe
#         df_display = pd.DataFrame(results).drop(columns=["_ticker_full"])

#         # Colour-code day change
#         def style_df(df):
#             styled = df.style.format({
#                 "Close (₹)": "₹{:.2f}",
#                 "20D High (₹)": "₹{:.2f}",
#                 "20D MA (₹)": "₹{:.2f}",
#                 "% Above 20D High": "{:+.2f}%",
#                 "Day Change (%)": "{:+.2f}%",
#                 "Volume Ratio": "{:.2f}×",
#             })

#             def color_change(val):
#                 color = "#198754" if val > 0 else "#dc3545"
#                 return f"color: {color}; font-weight: 600"

#             styled = styled.applymap(color_change, subset=["Day Change (%)", "% Above 20D High"])
#             styled = styled.applymap(
#                 lambda v: "color: #fd7e14; font-weight: 600",
#                 subset=["Volume Ratio"]
#             )
#             return styled

#         st.dataframe(
#             style_df(df_display),
#             use_container_width=True,
#             hide_index=True,
#             height=min(600, 50 + len(df_display) * 38),
#         )

#         # ── Download button ──
#         csv = df_display.to_csv(index=False)
#         st.download_button(
#             label="⬇ Download CSV",
#             data=csv,
#             file_name=f"breakouts_{scan_ts.strftime('%Y%m%d_%H%M') if scan_ts else 'today'}.csv",
#             mime="text/csv",
#         )

#     # ── Errors (collapsed) ──
#     if st.session_state.errors:
#         with st.expander(f"⚠️ {len(st.session_state.errors)} tickers had errors (click to expand)"):
#             for e in st.session_state.errors[:20]:
#                 st.caption(f"`{e['ticker']}` — {e['error']}")

# # ── Methodology expander ──────────────────────────────────────────────────────
# with st.expander("📖 How the breakout logic works"):
#     st.markdown("""
# **Triple-confirmation breakout scan — all 3 must be true:**

# | Condition | Indicator | What it means |
# |---|---|---|
# | `Close > 20-Day High` | Rolling max of High over 20 days | Price broke above recent resistance |
# | `Volume > 1.5× 10-Day Avg` | Rolling mean of Volume over 10 days | Unusual buying activity confirms the move |
# | `Close > 20-Day MA` | Rolling mean of Close over 20 days | Stock is in an uptrend |

# **Why triple-confirmation?**
# - Price alone can be a false breakout (thin/manipulated)
# - Volume alone without price is meaningless
# - MA alone just tells you trend, not momentum
# - Together: institutional-grade conviction signal

# **Data source:** Yahoo Finance (yfinance) — NSE daily OHLCV, 3 months lookback.
#     """)

# # ── Auto-rerun every 30 min ───────────────────────────────────────────────────
# # Streamlit re-runs the script; we just sleep until the next needed refresh.
# if st.session_state.results is not None:
#     elapsed = time.time() - st.session_state.last_scan_time
#     remaining = REFRESH_INTERVAL - elapsed
#     if remaining > 0:
#         # Show countdown and schedule a rerun
#         mins = int(remaining // 60)
#         secs = int(remaining % 60)
#         st.caption(f"🔄 Auto-refreshing in {mins}m {secs}s")
#         time.sleep(min(remaining, 60))  # recheck every 60s
#         st.rerun()
