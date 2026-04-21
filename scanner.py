import yfinance as yf
import pandas as pd
from datetime import datetime
from nifty500_stocks import NIFTY500_STOCKS


def scan_breakouts(progress_callback=None):
    """
    Scans all Nifty 500 stocks for breakout conditions.

    Breakout = ALL 3 conditions met:
      1. Close > 20-day rolling high (price breakout above resistance)
      2. Volume > 1.5x 10-day avg volume (volume confirmation)
      3. Close > 20-day moving average (above trend)

    Returns a list of dicts with breakout stock details.
    """
    results = []
    errors = []
    total = len(NIFTY500_STOCKS)

    for i, ticker in enumerate(NIFTY500_STOCKS):
        if progress_callback:
            progress_callback(i + 1, total, ticker)

        try:
            df = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)

            if df.empty or len(df) < 21:
                continue

            # Flatten multi-level columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df["20DMA"] = df["Close"].rolling(20).mean()
            df["10VolAvg"] = df["Volume"].rolling(10).mean()
            df["20High"] = df["High"].rolling(20).max()

            latest = df.iloc[-1]
            prev = df.iloc[-2]

            close = float(latest["Close"])
            high_20 = float(latest["20High"])
            vol = float(latest["Volume"])
            vol_avg = float(latest["10VolAvg"])
            dma_20 = float(latest["20DMA"])
            prev_close = float(prev["Close"])

            # Skip if any indicator is NaN
            if any(pd.isna(v) for v in [close, high_20, vol, vol_avg, dma_20]):
                continue

            is_breakout = (
                close > high_20
                and vol > 1.5 * vol_avg
                and close > dma_20
            )

            if is_breakout:
                vol_ratio = round(vol / vol_avg, 2)
                pct_above_high = round(((close - high_20) / high_20) * 100, 2)
                day_change = round(((close - prev_close) / prev_close) * 100, 2)

                results.append({
                    "Ticker": ticker.replace(".NS", ""),
                    "Close (₹)": round(close, 2),
                    "20D High (₹)": round(high_20, 2),
                    "% Above 20D High": pct_above_high,
                    "Day Change (%)": day_change,
                    "Volume Ratio": vol_ratio,
                    "20D MA (₹)": round(dma_20, 2),
                    "_ticker_full": ticker,
                })

        except Exception as e:
            errors.append({"ticker": ticker, "error": str(e)})

    # Sort by volume ratio descending (strongest breakouts first)
    results.sort(key=lambda x: x["Volume Ratio"], reverse=True)

    return results, errors, datetime.now()
