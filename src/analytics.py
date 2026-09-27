"""Analytics helpers: moving averages, returns, resampling, summaries."""

from __future__ import annotations

import pandas as pd


def add_moving_averages(df: pd.DataFrame, col: str, windows: list[int],
                        group: str | None = None) -> pd.DataFrame:
    """Add MA_<w> columns per group (or globally if group is None)."""
    df = df.sort_values("date").copy()
    for w in windows:
        ma_col = f"MA_{w}"
        if group:
            df[ma_col] = (df.groupby(group)[col]
                            .transform(lambda s: s.rolling(w, min_periods=1).mean()))
        else:
            df[ma_col] = df[col].rolling(w, min_periods=1).mean()
    return df


def daily_returns(df: pd.DataFrame, col: str = "close",
                  group: str = "ticker") -> pd.DataFrame:
    df = df.sort_values("date").copy()
    df["daily_return_pct"] = df.groupby(group)[col].pct_change() * 100
    return df


def resample_mean(df: pd.DataFrame, col: str, freq: str = "W",
                  group: str | None = None) -> pd.DataFrame:
    """Resample to freq (W/M), mean of col; keeps group column if given."""
    df = df.set_index("date")
    if group:
        out = (df.groupby([group, pd.Grouper(freq=freq)])[col]
                 .mean().reset_index())
    else:
        out = df[[col]].resample(freq).mean().reset_index()
    return out


def kpi_summary(df: pd.DataFrame, col: str,
                group: str | None = None) -> pd.DataFrame:
    """Per-group (or overall): latest, previous, change %, min, max, mean."""
    df = df.sort_values("date")
    if group:
        groups = df[group].unique()
    else:
        groups = [None]
    rows = []
    for g in groups:
        sub = df if g is None else df[df[group] == g]
        vals = sub[col].dropna()
        if len(vals) < 2:
            continue
        latest, prev = vals.iloc[-1], vals.iloc[-2]
        rows.append({
            "group": g if g is not None else "all",
            "latest": round(float(latest), 2),
            "prev": round(float(prev), 2),
            "change_pct": round((latest - prev) / abs(prev) * 100, 2)
            if prev != 0 else 0.0,
            "min": round(float(vals.min()), 2),
            "max": round(float(vals.max()), 2),
            "mean": round(float(vals.mean()), 2),
        })
    return pd.DataFrame(rows)


def per_capita(df: pd.DataFrame, count_col: str, pop_col: str = "population",
               per: int = 100_000) -> pd.Series:
    return df[count_col] / df[pop_col] * per
