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


def calculate_ma_ratio_diff(close: pd.Series, short_ma: int, long_ma: int) -> float:
    """Calculate (MA_short/MA_long - 1) relative difference"""
    min_required = max(short_ma, long_ma)
    if len(close) < min_required:
        return 0.0
    
    ma_short = close.rolling(window=short_ma).mean().iloc[-1]
    ma_long = close.rolling(window=long_ma).mean().iloc[-1]
    
    if pd.isna(ma_short) or pd.isna(ma_long) or ma_long == 0:
        return 0.0
    
    return (ma_short / ma_long) - 1


def compute_momentum(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None, 
                    short_ma: int = 5, long_ma: int = 20) -> pd.DataFrame:
    """Calculate momentum factor using MA: (MA_short/MA_long - 1) / avg(MA_short/MA_long - 1)
    
    Args:
        history: Historical price data
        top_spot: Optional spot data (unused)
        short_ma: Short period moving average (default: 5)
        long_ma: Long period moving average (default: 20)
    """
    rows: List[dict] = []
    ma_ratio_diffs: List[float] = []
    
    min_required = max(short_ma, long_ma)
    
    # First pass: calculate (MA_short/MA_long - 1) for all stocks
    stock_ma_data = {}
    for code, df in history.items():
        if df is None or df.empty or len(df) < min_required:
            continue
        
        df_sorted = df.sort_values("日期")
        close = df_sorted["收盘"]
        
        ma_ratio_diff = calculate_ma_ratio_diff(close, short_ma, long_ma)
        if ma_ratio_diff is not None:
            stock_ma_data[code] = ma_ratio_diff
            ma_ratio_diffs.append(ma_ratio_diff)
    
    # Calculate average (MA_short/MA_long - 1)
    avg_ma_ratio_diff = np.mean(ma_ratio_diffs) if ma_ratio_diffs else 1.0
    if avg_ma_ratio_diff == 0:
        avg_ma_ratio_diff = 1.0  # Avoid division by zero
    
    # Second pass: calculate momentum factor
    for code, ma_ratio_diff in stock_ma_data.items():
        momentum = ma_ratio_diff / avg_ma_ratio_diff
        rows.append({
            "代码": code, 
            "动量因子": momentum,
            f"MA{short_ma}/MA{long_ma}相对差值": ma_ratio_diff
        })
    
    return pd.DataFrame(rows)


# Configuration
DEFAULT_SHORT_MA = 3
DEFAULT_LONG_MA = 30

def compute_momentum_with_default_params(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Wrapper function that uses the default MA parameters"""
    result = compute_momentum(history, top_spot, DEFAULT_SHORT_MA, DEFAULT_LONG_MA)
    
    # Rename the dynamic column to a fixed name for the factor definition
    dynamic_col = f"MA{DEFAULT_SHORT_MA}/MA{DEFAULT_LONG_MA}相对差值"
    if dynamic_col in result.columns:
        result = result.rename(columns={dynamic_col: "MA相对差值"})
    
    return result

MOMENTUM_FACTOR = Factor(
    id="momentum",
    name="动量因子",
    description=f"基于移动平均线的动量因子：(MA{DEFAULT_SHORT_MA}/MA{DEFAULT_LONG_MA}-1)/avg(MA{DEFAULT_SHORT_MA}/MA{DEFAULT_LONG_MA}-1)",
    columns=[
        {"key": "动量因子", "label": "动量因子", "type": "number", "sortable": True},
        {"key": "动量评分", "label": "动量评分", "type": "score", "sortable": True},
        {"key": "MA相对差值", "label": f"MA{DEFAULT_SHORT_MA}/MA{DEFAULT_LONG_MA}相对差值", "type": "number", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_momentum_with_default_params(history, top_spot),
)

MODULE_FACTORS = [MOMENTUM_FACTOR]
