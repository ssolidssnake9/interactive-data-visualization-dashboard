"""Tests for analytics helpers (no Streamlit, no network)."""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from analytics import (add_moving_averages, daily_returns, kpi_summary,
                       per_capita, resample_mean)


def _df():
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=6, freq="D"),
        "ticker": ["A", "A", "A", "B", "B", "B"],
        "close": [10.0, 12.0, 11.0, 20.0, 22.0, 21.0],
    })


class TestAnalytics(unittest.TestCase):
    def test_moving_average(self):
        out = add_moving_averages(_df(), "close", [2], group="ticker")
        a = out[out.ticker == "A"]["MA_2"].tolist()
        self.assertEqual(a, [10.0, 11.0, 11.5])

    def test_daily_returns(self):
        out = daily_returns(_df())
        a = out[out.ticker == "A"]["daily_return_pct"].tolist()
        self.assertTrue(pd.isna(a[0]))
        self.assertAlmostEqual(a[1], 20.0)

    def test_kpi_summary(self):
        k = kpi_summary(_df(), "close", "ticker")
        ra = k[k.group == "A"].iloc[0]
        self.assertEqual(ra["latest"], 11.0)
        self.assertAlmostEqual(ra["change_pct"], -8.333, places=2)

    def test_resample(self):
        out = resample_mean(_df(), "close", freq="W", group="ticker")
        self.assertEqual(len(out), 2)

    def test_per_capita(self):
        df = pd.DataFrame({"cases": [500], "population": [1_000_000]})
        self.assertAlmostEqual(per_capita(df, "cases").iloc[0], 50.0)


if __name__ == "__main__":
    unittest.main()
