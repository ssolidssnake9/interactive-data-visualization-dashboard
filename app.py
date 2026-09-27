"""Interactive Data Visualization Dashboard (Streamlit).

Run:  streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.analytics import (add_moving_averages, daily_returns, kpi_summary,
                           per_capita, resample_mean)

DATA_DIR = Path(__file__).resolve().parent / "data"

st.set_page_config(page_title="InsightBoard", page_icon="📊", layout="wide")
st.title("📊 InsightBoard — raw data → consumer insights")

# ---------------------------------------------------------------- sidebar
dataset = st.sidebar.selectbox(
    "Dataset", ["Stocks (sample)", "Public health (sample)", "Upload CSV"])

uploaded = None
if dataset == "Upload CSV":
    uploaded = st.sidebar.file_uploader("CSV with a date column", type="csv")
    if uploaded is None:
        st.info("Upload a CSV to begin — it needs a date-like column.")
        st.stop()

# ---------------------------------------------------------------- loading
@st.cache_data
def load(name: str) -> pd.DataFrame:
    if name == "Stocks (sample)":
        df = pd.read_csv(DATA_DIR / "stocks.csv", parse_dates=["date"])
        return df
    df = pd.read_csv(DATA_DIR / "public_health.csv", parse_dates=["date"])
    return df

if uploaded is not None:
    df = pd.read_csv(uploaded)
    date_col = next((c for c in df.columns
                     if "date" in c.lower() or "time" in c.lower()), df.columns[0])
    df = df.rename(columns={date_col: "date"})
    df["date"] = pd.to_datetime(df["date"])
    num_cols = df.select_dtypes("number").columns.tolist()
    metric = st.sidebar.selectbox("Metric column", num_cols)
    group_col = st.sidebar.selectbox(
        "Group column (optional)", ["(none)"] + df.select_dtypes("object").columns.tolist())
    group_col = None if group_col == "(none)" else group_col
    CONFIG = {"metric": metric, "group": group_col, "kind": "generic"}
else:
    df = load(dataset)
    CONFIG = ({"metric": "close", "group": "ticker", "kind": "stocks"}
              if dataset.startswith("Stocks")
              else {"metric": "new_cases", "group": "region", "kind": "health"})

metric, group, kind = CONFIG["metric"], CONFIG["group"], CONFIG["kind"]

# ---------------------------------------------------------------- filters
st.sidebar.header("Filters")
min_d, max_d = df["date"].min().date(), df["date"].max().date()
start, end = st.sidebar.slider("Date range", min_d, max_d, (min_d, max_d))
mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)

groups = sorted(df[group].unique()) if group else []
picked = (st.sidebar.multiselect(f"Select {group}", groups, default=groups)
          if group else [])
if group:
    mask &= df[group].isin(picked)

freq = st.sidebar.selectbox("Granularity", ["Daily", "Weekly", "Monthly"])
freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "M"}
ma_windows = st.sidebar.multiselect("Moving averages", [7, 30, 90], default=[7, 30])

fdf = df[mask].copy()
if fdf.empty:
    st.warning("No data in the selected range — widen the filters.")
    st.stop()

# health: optional per-capita normalization
if kind == "health" and st.sidebar.checkbox("Per 100k residents", value=True):
    fdf = fdf.copy()
    fdf[metric] = per_capita(fdf, metric)
    metric_label = f"{metric} (per 100k)"
else:
    metric_label = metric

# ---------------------------------------------------------------- KPIs
st.subheader("Key figures")
kpis = kpi_summary(fdf, metric, group)
cols = st.columns(min(len(kpis), 4) or 1)
for i, row in kpis.head(4).iterrows():
    delta = f"{row['change_pct']:+.2f}% vs prev"
    cols[i % 4].metric(f"{row['group']} — latest {metric_label}",
                       f"{row['latest']:,}", delta)

# ---------------------------------------------------------------- trends
st.subheader(f"Trend — {metric_label}")
plot_df = add_moving_averages(fdf, metric, ma_windows, group)
if group:
    pivot = plot_df.pivot_table(index="date", columns=group,
                                values=metric, aggfunc="mean")
    if freq != "Daily":
        pivot = pivot.resample(freq_map[freq]).mean()
    st.line_chart(pivot)
    with st.expander("Moving averages"):
        ma_cols = [f"MA_{w}" for w in ma_windows]
        ma_pivot = plot_df.pivot_table(index="date", columns=group,
                                       values=ma_cols[0], aggfunc="mean")
        st.line_chart(ma_pivot)
else:
    ts = plot_df.set_index("date")[[metric] + [f"MA_{w}" for w in ma_windows]]
    if freq != "Daily":
        ts = ts.resample(freq_map[freq]).mean()
    st.line_chart(ts)

# ---------------------------------------------------------------- breakdown
c1, c2 = st.columns(2)
with c1:
    st.subheader("Distribution by group" if group else "Summary stats")
    if group:
        st.bar_chart(fdf.groupby(group)[metric].mean())
    else:
        st.dataframe(fdf[metric].describe().to_frame().T, use_container_width=True)
with c2:
    st.subheader("Volatility (daily % change)" if kind == "stocks" else "7-day average")
    if kind == "stocks":
        ret = daily_returns(fdf, metric, group)
        vol = ret.groupby(group)["daily_return_pct"].std().round(2)
        st.bar_chart(vol)
        st.caption("Std dev of daily returns — higher = wilder ride.")
    else:
        roll = (fdf.sort_values("date").groupby(group)[metric]
                   .transform(lambda s: s.rolling(7, min_periods=1).mean()))
        fdf_roll = fdf.assign(roll7=roll)
        piv = fdf_roll.pivot_table(index="date", columns=group,
                                   values="roll7", aggfunc="mean")
        st.line_chart(piv)

# ---------------------------------------------------------------- data
with st.expander("Underlying data & summary table"):
    st.dataframe(kpis, use_container_width=True)
    st.dataframe(fdf.head(200), use_container_width=True)
    st.download_button("Download filtered CSV",
                       fdf.to_csv(index=False), "filtered.csv", "text/csv")

st.caption("Sample datasets are synthetic and for demo purposes. Upload your own CSV for real analysis.")
