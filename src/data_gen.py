"""Generate sample datasets: synthetic stock prices and public-health time series."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEED = 42


def gen_stocks(path: Path = DATA_DIR / "stocks.csv") -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    dates = pd.date_range("2024-01-02", "2025-12-31", freq="B")
    frames = []
    specs = {"NOVA": (120.0, 0.0012, 0.022), "HELIX": (85.0, 0.0008, 0.031),
             "ORBIT": (210.0, 0.0005, 0.016)}
    for ticker, (start, drift, vol) in specs.items():
        rets = rng.normal(drift, vol, len(dates))
        # a couple of regime shocks so trends are visible
        rets[200:230] *= -3
        rets[400:430] *= 2.5
        close = start * np.exp(np.cumsum(rets))
        volume = rng.integers(800_000, 6_000_000, len(dates))
        frames.append(pd.DataFrame({
            "date": dates, "ticker": ticker,
            "close": close.round(2), "volume": volume,
        }))
    df = pd.concat(frames, ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def gen_health(path: Path = DATA_DIR / "public_health.csv") -> pd.DataFrame:
    rng = np.random.default_rng(SEED + 1)
    dates = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    frames = []
    for region, pop, peak in [("North", 4_200_000, 950), ("South", 6_800_000, 1400),
                             ("East", 3_100_000, 620), ("West", 5_400_000, 1100)]:
        t = np.arange(len(dates))
        # two seasonal waves + noise
        wave = (peak * np.exp(-((t - 120) / 45) ** 2)
                + 0.7 * peak * np.exp(-((t - 480) / 55) ** 2))
        cases = np.maximum(0, wave + rng.normal(0, peak * 0.08, len(dates))).astype(int)
        hosp = np.maximum(0, (cases * 0.09 + rng.normal(0, 8, len(dates))).astype(int))
        frames.append(pd.DataFrame({
            "date": dates, "region": region, "population": pop,
            "new_cases": cases, "new_hospitalizations": hosp,
        }))
    df = pd.concat(frames, ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


if __name__ == "__main__":
    s = gen_stocks()
    h = gen_health()
    print(f"stocks: {len(s)} rows, {s['ticker'].nunique()} tickers")
    print(f"health: {len(h)} rows, {h['region'].nunique()} regions")
