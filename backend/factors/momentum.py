from __future__ import annotations

from typing import Dict, Optional, List
import pandas as pd
import numpy as np

from models import Factor

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False


def calculate_momentum_simple(df: pd.DataFrame) -> float:
    """Calculate (昨开-昨收)/(昨低-今低)-1"""
    if len(df) < 2:
        return 0.0
    
    # Convert date column to datetime for proper sorting if needed
    df_copy = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_copy['日期']):
        df_copy['日期'] = pd.to_datetime(df_copy['日期'])
    
    # Sort by date (most recent last)
    df_sorted = df_copy.sort_values("日期", ascending=True)
    df_sorted = df_sorted.reset_index(drop=True)
    
    # Get yesterday's and today's data
    yesterday = df_sorted.iloc[-2]
    today = df_sorted.iloc[-1]
    
    yesterday_open = yesterday["开盘"]
    yesterday_close = yesterday["收盘"]
    yesterday_low = yesterday["最低"]
    today_low = today["最低"]
    
    # Check for invalid data
    if pd.isna(yesterday_open) or pd.isna(yesterday_close) or pd.isna(yesterday_low) or pd.isna(today_low):
        return 0.0
    
    yesterday_open = float(yesterday_open)
    yesterday_close = float(yesterday_close)
    yesterday_low = float(yesterday_low)
    today_low = float(today_low)
    
    denominator = yesterday_low - today_low
    if denominator == 0:
        return 0.0
    
    return (yesterday_open - yesterday_close) / denominator - 1


def compute_momentum(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Calculate momentum factor using formula: (昨开-昨收)/(昨低-今低)-1
    
    Args:
        history: Historical price data
        top_spot: Optional spot data (unused)
    """
    rows: List[dict] = []
    
    for code, df in history.items():
        if df is None or df.empty or len(df) < 2:
            continue
        
        momentum = calculate_momentum_simple(df)
        rows.append({
            "代码": code, 
            "动量因子": momentum
        })
    
    # Sort by momentum factor from high to low
    df_result = pd.DataFrame(rows)
    if not df_result.empty:
        df_result = df_result.sort_values("动量因子", ascending=False)
    
    return df_result


MOMENTUM_FACTOR = Factor(
    id="momentum",
    name="动量因子",
    description="简单动量因子：(昨开-昨收)/(昨低-今低)-1，从大到小排序",
    columns=[
        {"key": "动量因子", "label": "动量因子", "type": "number", "sortable": True},
        {"key": "动量评分", "label": "动量评分", "type": "score", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_momentum(history, top_spot),
)

MODULE_FACTORS = [MOMENTUM_FACTOR]
