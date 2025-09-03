from __future__ import annotations

from typing import Dict, Optional, List
import pandas as pd

from models import Factor


def compute_momentum(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None, period: int = 20) -> pd.DataFrame:
    rows: List[dict] = []
    for code, df in history.items():
        if df is None or df.empty or len(df) < period + 1:
            continue
        df_sorted = df.sort_values("日期")
        last_price = float(df_sorted["收盘"].iloc[-1])
        first_price = float(df_sorted["收盘"].iloc[-(period + 1)])
        momentum = (last_price - first_price) / first_price if first_price > 0 else 0
        rows.append({"代码": code, "动量因子": momentum})
    return pd.DataFrame(rows)


MOMENTUM_FACTOR = Factor(
    id="momentum",
    name="动量因子",
    description="近20日价格涨跌幅",
    columns=[
        {"key": "动量因子", "label": "动量因子", "type": "percent", "sortable": True},
        {"key": "动量评分", "label": "动量评分", "type": "score", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_momentum(history, top_spot, period=20),
)

MODULE_FACTORS = [MOMENTUM_FACTOR]
