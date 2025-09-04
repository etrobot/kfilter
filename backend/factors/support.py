from __future__ import annotations

from typing import Dict, Optional, List
import pandas as pd
import numpy as np

from models import Factor


def days_from_longest_candle(candles, window_size):
    """计算最长K线实体到最新价格的天数"""
    # 取最后 window_size+1 根K线，这样窗口内的每根K线都有昨收数据
    # 实际分析的是最后 window_size 根K线
    extended_window = candles[-(window_size + 1):]
    
    # 找到最大实体的索引（使用相对昨收的幅度）
    # 从索引1开始，因为索引0是用来提供昨收数据的
    max_body_idx = max(range(1, len(extended_window)), 
                      key=lambda i: calculate_relative_body_length(extended_window, i))
    
    # 返回天数差（调整索引，因为我们从1开始计算）
    return len(extended_window) - max_body_idx


def calculate_relative_body_length(window, idx):
    """计算K线实体相对昨收的幅度"""
    candle = window[idx]
    
    # 获取昨收价格（前一天的收盘价）
    # 现在每个K线都有昨收数据，不需要特殊处理
    prev_close = window[idx - 1]['close']
    
    if prev_close == 0:
        return 0.0
    
    # 计算实体相对昨收的幅度
    body_length_ratio = abs(candle['close'] - candle['open']) / prev_close
    return body_length_ratio


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
            
        df_sorted = df.sort_values("日期")
        
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
        # We need window_size + 1 candles to have proper previous close for all window candles
        actual_window = min(window_size, len(candles) - 1)
        
        days_from_longest = days_from_longest_candle(candles, actual_window)
        
        # Support factor: days from longest candle (more distant longest candle = better support)
        # Normalize to 0-1 range, where farther from recent = higher score
        support_factor_base = (days_from_longest / (actual_window - 1)) if actual_window > 1 else 0
        
        # Get the window for price ratio calculation
        window = candles[-actual_window:]
        
        # Use window first price / window last price as described
        # For support factor, we want higher values when price has declined from window start

        price_ratio = (window[-1]['close']-window[-1]['open'])/ window[0]['close']
        
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
        {"key": "支撑评分", "label": "支撑评分", "type": "score", "sortable": True},
        {"key": "最长K线天数", "label": f"最长K线天数({DEFAULT_WINDOW_SIZE}日)", "type": "number", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_support_with_default_window(history, top_spot),
)

MODULE_FACTORS = [SUPPORT_FACTOR]
