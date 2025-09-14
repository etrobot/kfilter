from __future__ import annotations

from typing import Dict, Optional, List
import pandas as pd
import numpy as np

from models import Factor


def calculate_days_from_longest_candle(df_window):
    """计算最长K线实体到最新价格的天数（向量化版本）"""
    if len(df_window) < 2:
        return 0
    
    # 计算相对昨收的实体幅度
    first_close = df_window.iloc[0]['收盘']
    body_lengths = (df_window.iloc[1:]['收盘'] - df_window.iloc[1:]['开盘']).abs() * 100 / first_close
    
    # 找到最大实体的索引（从后往前，所以相同长度时选择最近的）
    max_idx_rev = body_lengths.iloc[::-1].idxmax()
    
    # 返回天数差（从最后一天往前数）
    return len(df_window) - 1 - max_idx_rev + 1


def compute_support(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None, window_size: int = 60) -> pd.DataFrame:
    """Calculate support factor using days from longest candle
    
    Args:
        history: Historical price data
        top_spot: Optional spot data (unused)
        window_size: Number of days to look back for analysis (default: 60)
    """
    rows: List[dict] = []
    
    for code, df in history.items():
        # Require at least window_size + 1 days for meaningful analysis (extra day for previous close)
        if df is None or df.empty or len(df) < window_size + 1:
            continue
            
        # Convert date column to datetime for proper sorting if needed
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_copy['日期']):
            df_copy['日期'] = pd.to_datetime(df_copy['日期'])
        
        df_sorted = df_copy.sort_values("日期", ascending=True)
        
        # Convert DataFrame to list of candle dictionaries
        candles = []
        for _, row in df_sorted.iterrows():
            candles.append({
                'open': row['开盘'],
                'close': row['收盘'],
                'high': row['最高'],
                'low': row['最低']
            })
        
        # Calculate days from longest candle with specified window
        # We need window_size + 1 days for proper previous close reference
        actual_window = min(window_size, len(df_sorted) - 1)
        
        # Get the extended window data (window_size + 1 days)
        df_extended_window = df_sorted.iloc[-(actual_window + 1):]
        
        days_from_longest = calculate_days_from_longest_candle(df_extended_window)
        
        # Support factor: days from longest candle (more distant longest candle = better support)
        # Normalize to 0-1 range, where farther from recent = higher score
        support_factor_base = (days_from_longest / (actual_window - 1)) if actual_window > 1 else 0
        
        # Get the window for price ratio calculation
        window = candles[-actual_window:]
        
        # Use window first price / window last price as described
        # For support factor, we want higher values when price has declined from window start

        # Calculate price ratio: (昨开-昨收)/(昨低-今低)-1
        if len(window) >= 2:
            yesterday = window[-2]
            today = window[-1]
            yesterday_open = yesterday['open']
            yesterday_close = yesterday['close']
            yesterday_low = yesterday['low']
            today_low = today['low']
            
            denominator = yesterday_low - today_low
            if denominator != 0:
                price_ratio = (yesterday_open - yesterday_close) * 2 / denominator
            else:
                price_ratio = 1.0
        else:
            price_ratio = 1.0
        
        # Final support factor: combine time factor with price movement
        # Higher values indicate stronger support (recent longest candle + price decline)
        support_factor = support_factor_base * price_ratio
        
        rows.append({
            "代码": code, 
            "支撑因子": support_factor,
            f"最长K线天数_{window_size}日": days_from_longest,
        })
    
    return pd.DataFrame(rows)


# Configuration
DEFAULT_WINDOW_SIZE = 30

def compute_support_with_default_window(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Wrapper function that uses the default window size"""
    result = compute_support(history, top_spot, DEFAULT_WINDOW_SIZE)
    
    # Rename the dynamic column to a fixed name for the factor definition
    dynamic_col = f"最长K线天数_{DEFAULT_WINDOW_SIZE}日"
    if dynamic_col in result.columns:
        result = result.rename(columns={dynamic_col: "最长K线天数"})
    
    return result

SUPPORT_FACTOR = Factor(
    id="support",
    name="支撑因子",
    description=f"基于最长K线实体距离的支撑强度：计算{DEFAULT_WINDOW_SIZE}日窗口内最长K线实体（相对昨收幅度）到当前的天数，天数越多支撑越强，值越大越好",
    columns=[
        {"key": "支撑因子", "label": "支撑因子", "type": "number", "sortable": True},
        # {"key": "支撑评分", "label": "支撑评分", "type": "score", "sortable": True},
        {"key": "最长K线天数", "label": f"{DEFAULT_WINDOW_SIZE}日最长K线距今", "type": "number", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_support_with_default_window(history, top_spot),
)

MODULE_FACTORS = [SUPPORT_FACTOR]
