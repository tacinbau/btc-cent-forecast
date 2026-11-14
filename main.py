#!/usr/bin/env python3
"""btc-cent-forecast-01 entry: forecast BTC/USD 240 minutes ahead.

Model (fit only on the kit's six practice cases, walk-forward, 4h spacing):
  1. Spike-robust base. The checkpoint close comes from a single Orca pool and
     occasionally dislocates for a minute (e.g. a -1.63% one-minute print that
     reverts within minutes). If the last close deviates from the median of the
     last 15 closes by more than 0.3% (in log terms), the close is treated as
     dislocated and the 15-minute median is used instead; otherwise the last
     close itself is the base. This keeps the forecast centred on the current
     price in normal times and avoids paying a dislocation's full size.
  2. Damped trend. OLS slope of log price on 15-minute medians over the last
     720 minutes (48 points), extrapolated 240 minutes and damped by 0.3.
     Short-window trends hurt (noise dominates); the 12h trend, heavily
     damped, is a small, consistent improvement over persistence. The trend
     adjustment is clamped to +/-3% in log terms (never binds on practice
     data, max 0.23%) as a guard against a wild guess on unseen data.

Everything is deterministic, standard library only, no network, and runs in
well under a second per case.

Validation on the kit's practice cases (walk-forward, checkpoints 4h apart):
  persistence baseline mean abs error: 41,787 cents
  this entry:                          33,243 cents  (-20.4%)
On the five practice answers reconstructable from the kit itself
(p00..p04, each answer is the next case's checkpoint close):
  persistence: 47,055 cents; this entry: 45,402 cents  (-3.5%)
Per-case (240-min spacing) it beats persistence in all six practice cases.
"""

import json
import math
import os
import sys

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999

# Median window for the spike-robust base (minutes).
BASE_MEDIAN_WINDOW = 15
# Log-deviation above which the last close counts as dislocated.
DISLOCATION_THRESHOLD = 0.003
# Trend window (minutes) and damping applied to the extrapolated slope.
TREND_WINDOW_MINUTES = 720
TREND_DAMP = 0.3
# Horizon to forecast (minutes).
HORIZON_MINUTES = 240
# Medians are taken over this many minutes for the trend series.
TREND_MEDIAN_STEP = 15
# Safety clamp on the trend adjustment (log points): the largest 4h move in
# the practice window is 2.25%, and the largest trend adjustment the model
# ever produces there is 0.23%, so 3% never binds on sane data — it only
# stops a wild guess if the trend estimate ever goes wrong on unseen data.
MAX_TREND_LOG = 0.03


def _median(values):
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return 0.5 * (s[mid - 1] + s[mid])


def _ols_slope(xs):
    """Slope of the ordinary least-squares line through xs (unit spacing)."""
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(xs) / n
    sxy = 0.0
    sxx = 0.0
    for i, y in enumerate(xs):
        dx = i - mean_x
        sxy += dx * (y - mean_y)
        sxx += dx * dx
    return sxy / sxx if sxx > 0.0 else 0.0


def _price5(x):
    """Keep a price on the grid's 5 decimals and inside (0, 10,000,000)."""
    if not math.isfinite(x):
        x = 75000.0
    x = min(MAX_PRICE, max(MIN_PRICE, x))
    return round(x, 5)


def forecast(prices):
    """One forecast price (USD) from a list of 1-minute closes, oldest first."""
    finite = [p for p in prices if isinstance(p, (int, float)) and math.isfinite(p) and p > 0]
    if not finite:
        return _price5(75000.0)
    lp = [math.log(p) for p in finite]
    last = lp[-1]

    # 1. Spike-robust base.
    window = lp[-BASE_MEDIAN_WINDOW:]
    med = _median(window)
    base = med if abs(last - med) > DISLOCATION_THRESHOLD else last

    # 2. Damped trend from 15-minute medians over the last 12 hours.
    trend = 0.0
    if len(lp) > TREND_MEDIAN_STEP:
        points = []
        end = len(lp) - 1
        start = max(TREND_MEDIAN_STEP - 1, end - TREND_WINDOW_MINUTES)
        i = end
        while i >= start:
            lo = i - TREND_MEDIAN_STEP + 1
            points.append(_median(lp[lo:i + 1]))
            i -= TREND_MEDIAN_STEP
        points.reverse()
        if len(points) >= 3:
            # Slope per 15-minute step; 240 minutes is 16 steps.
            raw = TREND_DAMP * _ols_slope(points) * (HORIZON_MINUTES / TREND_MEDIAN_STEP)
            trend = min(MAX_TREND_LOG, max(-MAX_TREND_LOG, raw))

    return _price5(math.exp(base + trend))


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    inputs = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".in"))
    for filename in inputs:
        case_id = filename[:-len(".in")]
        with open(os.path.join(INPUT_DIR, filename), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        markets = case.get("markets") or []
        if len(markets) != 1:
            raise ValueError(f"{filename} does not hold exactly one market")
        price = forecast(markets[0].get("prices") or [])
        out = {"forecasts": [{"case": case_id, "price": price}]}
        with open(os.path.join(OUTPUT_DIR, f"{case_id}.out"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
