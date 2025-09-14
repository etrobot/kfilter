from __future__ import annotations

from typing import Dict, Optional, List
import pandas as pd
import numpy as np

from models import Factor



def calculate_momentum_simple(df: pd.DataFrame) -> float:
    """Calculate (后段最低点 - 前段最低点) / 整段最长K线"""
    if len(df) < 2:
        return 0.0
    
    # Convert date column to datetime for proper sorting if needed
    df_copy = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_copy['日期']):
        df_copy['日期'] = pd.to_datetime(df_copy['日期'])
    
    # Sort by date (oldest first)
    df_sorted = df_copy.sort_values("日期", ascending=True)
    df_sorted = df_sorted.reset_index(drop=True)
    
    # Calculate the necessary values
    # 前段最低点 - minimum price in first half of period
    half_idx = len(df_sorted) // 2
    first_half_low = df_sorted.iloc[:half_idx]["最低"].min()
    
    # 后段最低点 - minimum price in second half of period
    second_half_low = df_sorted.iloc[half_idx:]["最低"].min()
    
    # 整段最长K线 - maximum daily body length (absolute |close - open|) in entire period
    max_daily_change = (df_sorted["收盘"] - df_sorted["开盘"]).abs().max()
    
    # Check for invalid data
    if pd.isna(first_half_low) or pd.isna(second_half_low) or pd.isna(max_daily_change):
        return 0.0
    
    first_half_low = float(first_half_low)
    second_half_low = float(second_half_low)
    max_daily_change = float(max_daily_change)
    
    if max_daily_change == 0:
        return 0.0
    
    return (second_half_low - first_half_low) / max_daily_change


def compute_momentum(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Calculate momentum factor using formula: (后段最低点 - 前段最低点) / 整段最长K线
    
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
    description="动量因子：(后段最低点 - 前段最低点) / 整段最长K线，从大到小排序",
    columns=[
        {"key": "动量因子", "label": "动量因子", "type": "number", "sortable": True},
        {"key": "动量评分", "label": "动量评分", "type": "score", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_momentum(history, top_spot),
)

MODULE_FACTORS = [MOMENTUM_FACTOR]
