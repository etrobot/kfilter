from __future__ import annotations

from typing import Dict, Optional, List
import pandas as pd

from models import Factor


def compute_support(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None, period: int = 5) -> pd.DataFrame:
    rows: List[dict] = []
    for code, df in history.items():
        if df is None or df.empty or len(df) < period:
            continue
        df_sorted = df.sort_values("日期")
        recent_lows = df_sorted["最低"].tail(period)
        support_level = float(recent_lows.mean())
        current_price = float(df_sorted["收盘"].iloc[-1])
        support_distance = (current_price - support_level) / support_level if support_level > 0 else 0
        rows.append({"代码": code, "支撑因子": support_distance, "支撑位": support_level})
    return pd.DataFrame(rows)


SUPPORT_FACTOR = Factor(
    id="support",
    name="支撑因子",
    description="近5日均低点与当前价的相对距离",
    columns=[
        {"key": "支撑因子", "label": "支撑因子", "type": "percent", "sortable": True},
        {"key": "支撑评分", "label": "支撑评分", "type": "score", "sortable": True},
        {"key": "支撑位", "label": "支撑位", "type": "number", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_support(history, top_spot, period=5),
)

MODULE_FACTORS = [SUPPORT_FACTOR]
