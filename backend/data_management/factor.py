from __future__ import annotations
import pandas as pd
from typing import Dict


def calculate_momentum_factor(history: Dict[str, pd.DataFrame], period: int = 20) -> pd.DataFrame:
    """Calculate momentum factor based on price returns over specified period"""
    momentum_data = []
    
    for code, df in history.items():
        if df is None or df.empty or len(df) < period + 1:
            continue
            
        df_sorted = df.sort_values("日期")
        
        # Calculate momentum as return over period
        if len(df_sorted) >= period + 1:
            last_price = float(df_sorted["收盘"].iloc[-1])
            first_price = float(df_sorted["收盘"].iloc[-(period + 1)])
            momentum = (last_price - first_price) / first_price if first_price > 0 else 0
            
            momentum_data.append({
                "代码": code,
                "动量因子": momentum
            })
    
    return pd.DataFrame(momentum_data)


def calculate_support_factor(history: Dict[str, pd.DataFrame], period: int = 5) -> pd.DataFrame:
    """Calculate support factor based on recent low prices"""
    support_data = []
    
    for code, df in history.items():
        if df is None or df.empty or len(df) < period:
            continue
            
        df_sorted = df.sort_values("日期")
        
        # Calculate support level as mean of recent lows
        recent_lows = df_sorted["最低"].tail(period)
        support_level = float(recent_lows.mean())
        
        # Current price distance to support
        current_price = float(df_sorted["收盘"].iloc[-1])
        support_distance = (current_price - support_level) / support_level if support_level > 0 else 0
        
        support_data.append({
            "代码": code,
            "支撑因子": support_distance,
            "支撑位": support_level
        })
    
    return pd.DataFrame(support_data)