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


def calculate_kdj(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 9) -> tuple:
    """Calculate KDJ indicator using talib or manual calculation"""
    if HAS_TALIB and len(high) >= period:
        try:
            k, d = talib.STOCH(high.values, low.values, close.values, 
                              fastk_period=period, slowk_period=3, slowd_period=3)
            j = 3 * k - 2 * d
            return k, d, j
        except Exception:
            pass
    
    # Manual KDJ calculation as fallback
    if len(high) < period:
        return None, None, None
    
    # Calculate RSV (Raw Stochastic Value)
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(50)  # Fill NaN with 50
    
    # Calculate K, D, J
    k = rsv.ewm(alpha=1/3).mean()  # K = 2/3 * prev_K + 1/3 * RSV
    d = k.ewm(alpha=1/3).mean()    # D = 2/3 * prev_D + 1/3 * K
    j = 3 * k - 2 * d             # J = 3K - 2D
    
    return k.values, d.values, j.values


def compute_momentum(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None, period: int = 9) -> pd.DataFrame:
    """Calculate momentum factor using KDJ: (J-D)/avg(J-D)"""
    rows: List[dict] = []
    jd_diffs: List[float] = []
    
    # First pass: calculate J-D for all stocks
    stock_jd_data = {}
    for code, df in history.items():
        if df is None or df.empty or len(df) < period + 5:
            continue
        
        df_sorted = df.sort_values("日期")
        high = df_sorted["最高"]
        low = df_sorted["最低"] 
        close = df_sorted["收盘"]
        
        k, d, j = calculate_kdj(high, low, close, period)
        if k is not None and d is not None and j is not None:
            # Use the latest values
            latest_j = j[-1] if not np.isnan(j[-1]) else 0
            latest_d = d[-1] if not np.isnan(d[-1]) else 0
            jd_diff = latest_j - latest_d
            
            stock_jd_data[code] = jd_diff
            jd_diffs.append(jd_diff)
    
    # Calculate average J-D
    avg_jd = np.mean(jd_diffs) if jd_diffs else 1.0
    if avg_jd == 0:
        avg_jd = 1.0  # Avoid division by zero
    
    # Second pass: calculate momentum factor
    for code, jd_diff in stock_jd_data.items():
        momentum = jd_diff / avg_jd
        rows.append({"代码": code, "动量因子": momentum})
    
    return pd.DataFrame(rows)


MOMENTUM_FACTOR = Factor(
    id="momentum",
    name="动量因子",
    description="基于KDJ指标的动量因子：(J-D)/avg(J-D)",
    columns=[
        {"key": "动量因子", "label": "动量因子", "type": "number", "sortable": True},
        {"key": "动量评分", "label": "动量评分", "type": "score", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_momentum(history, top_spot, period=9),
)

MODULE_FACTORS = [MOMENTUM_FACTOR]
