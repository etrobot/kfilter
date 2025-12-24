from __future__ import annotations

from typing import Dict, Optional, List
import pandas as pd
import numpy as np

from models import Factor



def calculate_momentum_simple(df: pd.DataFrame) -> float:
    """Calculate sum of candlestick bodies over last 10 days (bullish positive, bearish negative)"""
    if len(df) < 1:
        return 0.0
    
    # Convert date column to datetime for proper sorting if needed
    df_copy = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_copy['日期']):
        df_copy['日期'] = pd.to_datetime(df_copy['日期'])
    
    # Sort by date (oldest first) and take last 10 days
    df_sorted = df_copy.sort_values("日期", ascending=True)
    df_sorted = df_sorted.reset_index(drop=True)
    
    # Take last 10 trading days
    df_last_10 = df_sorted.tail(10)
    
    # Calculate body for each candle: close - open
    # Positive for bullish (阳线), negative for bearish (阴线)
    bodies = df_last_10["收盘"] - df_last_10["开盘"]
    
    # Check for invalid data
    if bodies.isna().any():
        # Sum only valid values
        total_body = bodies.dropna().sum()
    else:
        total_body = bodies.sum()
    
    # Convert to float
    if pd.isna(total_body):
        return 0.0
    
    return float(total_body)


def compute_momentum(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Calculate momentum factor using sum of last 10 days' candlestick bodies
    
    Args:
        history: Historical price data
        top_spot: Optional spot data (unused)
    """
    rows: List[dict] = []
    
    for code, df in history.items():
        if df is None or df.empty or len(df) < 1:
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
    description="动量因子：近十天K线涨跌幅实体总和（阳线为正，阴线为负），从大到小排序",
    columns=[
        {"key": "动量因子", "label": "动量因子", "type": "number", "sortable": True},
        {"key": "动量评分", "label": "动量评分", "type": "score", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_momentum(history, top_spot),
)

MODULE_FACTORS = [MOMENTUM_FACTOR]
