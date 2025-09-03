from __future__ import annotations

from typing import Dict, Optional, List
import pandas as pd
import numpy as np

from models import Factor


def compute_support(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Calculate support factor using MA convergence: min(ma5,ma10,ma20,ma60)/max(ma5,ma10,ma20,ma60)"""
    rows: List[dict] = []
    
    for code, df in history.items():
        if df is None or df.empty or len(df) < 60:  # Need at least 60 days for MA60
            continue
            
        df_sorted = df.sort_values("日期")
        close_prices = df_sorted["收盘"]
        
        # Calculate moving averages
        ma5 = close_prices.rolling(window=5).mean()
        ma10 = close_prices.rolling(window=10).mean()
        ma20 = close_prices.rolling(window=20).mean()
        ma60 = close_prices.rolling(window=60).mean()
        
        # Get the latest MA values
        latest_ma5 = ma5.iloc[-1] if not pd.isna(ma5.iloc[-1]) else 0
        latest_ma10 = ma10.iloc[-1] if not pd.isna(ma10.iloc[-1]) else 0
        latest_ma20 = ma20.iloc[-1] if not pd.isna(ma20.iloc[-1]) else 0
        latest_ma60 = ma60.iloc[-1] if not pd.isna(ma60.iloc[-1]) else 0
        
        # Calculate support factor: min(MA) / max(MA)
        ma_values = [latest_ma5, latest_ma10, latest_ma20, latest_ma60]
        ma_values = [ma for ma in ma_values if ma > 0]  # Filter out zero/invalid values
        
        if len(ma_values) >= 2:  # Need at least 2 valid MA values
            min_ma = min(ma_values)
            max_ma = max(ma_values)
            support_factor = min_ma / max_ma if max_ma > 0 else 0
            
            rows.append({
                "代码": code, 
                "支撑因子": support_factor,
                "MA5": latest_ma5,
                "MA10": latest_ma10,
                "MA20": latest_ma20,
                "MA60": latest_ma60
            })
    
    return pd.DataFrame(rows)


SUPPORT_FACTOR = Factor(
    id="support",
    name="支撑因子",
    description="移动平均线收敛度：min(MA5,MA10,MA20,MA60)/max(MA5,MA10,MA20,MA60)，值越大越好",
    columns=[
        {"key": "支撑因子", "label": "支撑因子", "type": "number", "sortable": True},
        {"key": "支撑评分", "label": "支撑评分", "type": "score", "sortable": True},
        {"key": "MA5", "label": "MA5", "type": "number", "sortable": True},
        {"key": "MA10", "label": "MA10", "type": "number", "sortable": True},
        {"key": "MA20", "label": "MA20", "type": "number", "sortable": True},
        {"key": "MA60", "label": "MA60", "type": "number", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_support(history, top_spot),
)

MODULE_FACTORS = [SUPPORT_FACTOR]
