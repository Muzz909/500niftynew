import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Breakout Debug", layout="wide")
st.title("🔍 Breakout Scanner — Debug Mode")

# Test with just 10 well-known stocks first
TEST_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "LT.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS"
]

st.markdown("Testing 10 stocks with **relaxed conditions** to verify data is flowing correctly.")
st.markdown("---")

rows = []
progress = st.progress(0)
status = st.empty()

for i, ticker in enumerate(TEST_STOCKS):
    progress.progress((i + 1) / len(TEST_STOCKS))
    status.text(f"Fetching {ticker}...")

    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty or len(df) < 21:
            rows.append({"Ticker": ticker, "C > 20H": "no data", "V > 1.5x": "no data", "C > 20DMA": "no data"})
            continue

        df["20DMA"]    = df["Close"].rolling(20).mean()
        df["10VolAvg"] = df["Volume"].rolling(10).mean()
        df["20High"]   = df["High"].rolling(20).max()

        latest = df.iloc[-1]
        close  = float(latest["Close"])
        high20 = float(latest["20High"])
        vol    = float(latest["Volume"])
        volavg = float(latest["10VolAvg"])
        dma20  = float(latest["20DMA"])

        c1 = close > high20
        c2 = vol > 1.5 * volavg
        c3 = close > dma20

        rows.append({
            "Ticker":          ticker.replace(".NS", ""),
            "Close ₹":         round(close, 1),
            "20D High ₹":      round(high20, 1),
            "Vol Ratio":       round(vol / volavg, 2),
            "20D MA ₹":        round(dma20, 1),
            "C > 20H":         "✅" if c1 else "❌",
            "V > 1.5×avg":     "✅" if c2 else "❌",
            "C > 20DMA":       "✅" if c3 else "❌",
            "Strict (all 3)":  "🔥" if (c1 and c2 and c3) else "—",
            "Relaxed (any 1)": "⚡" if (c1 or c2 or c3) else "—",
        })

    except Exception as e:
        rows.append({"Ticker": ticker, "Error": str(e)})

progress.empty()
status.empty()

st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("""
**How to read this:**
- `C > 20H` — Close broke above 20-day rolling high
- `V > 1.5×avg` — Volume surge (50%+ above 10-day avg)
- `C > 20DMA` — Close above 20-day moving average (uptrend)
- **Strict** = all 3 true → original scanner logic
- **Relaxed** = any 1 true → you should see several stocks here

If **Relaxed** is also all `—`, the data pipeline has a problem. Share a screenshot and I'll fix it.
""")















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
