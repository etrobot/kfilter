from __future__ import annotations

from typing import Dict, Optional, List
import pandas as pd
import numpy as np

from models import Factor


def calculate_macd(close_prices: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.Series:
    """计算MACD指标
    
    Args:
        close_prices: 收盘价序列
        fast_period: 快线周期 (默认12)
        slow_period: 慢线周期 (默认26)
        signal_period: 信号线周期 (默认9)
    
    Returns:
        MACD柱状图值 (DIF - DEA)
    """
    # 计算EMA
    ema_fast = close_prices.ewm(span=fast_period, adjust=False).mean()
    ema_slow = close_prices.ewm(span=slow_period, adjust=False).mean()
    
    # 计算DIF (快线 - 慢线)
    dif = ema_fast - ema_slow
    
    # 计算DEA (DIF的EMA)
    dea = dif.ewm(span=signal_period, adjust=False).mean()
    
    # 返回MACD柱状图 (DIF - DEA)
    macd = dif - dea
    
    return macd


def compute_support(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None, macd_window: int = 10) -> pd.DataFrame:
    """Calculate support factor using MACD absolute value sum
    
    近10个MACD绝对值总和越小越好，表示价格波动趋于平稳，可能形成支撑
    
    Args:
        history: Historical price data
        top_spot: Optional spot data (unused)
        macd_window: Number of recent MACD values to sum (default: 10)
    """
    rows: List[dict] = []
    
    for code, df in history.items():
        # 需要至少26+9+macd_window天的数据来计算MACD
        min_required_days = 26 + 9 + macd_window
        if df is None or df.empty or len(df) < min_required_days:
            continue
            
        # Convert date column to datetime for proper sorting if needed
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_copy['日期']):
            df_copy['日期'] = pd.to_datetime(df_copy['日期'])
        
        df_sorted = df_copy.sort_values("日期", ascending=True)
        
        # 计算MACD
        close_prices = df_sorted['收盘']
        macd_values = calculate_macd(close_prices)
        
        # 获取最近macd_window个MACD值
        recent_macd = macd_values.iloc[-macd_window:]
        
        # 计算MACD绝对值总和
        macd_abs_sum = recent_macd.abs().sum()
        
        # 支撑因子：MACD绝对值总和的倒数（值越小越好，所以取倒数让值越大越好）
        # 为了避免除以0，添加一个小常数
        support_factor = 1.0 / (macd_abs_sum + 0.0001)
        
        # 获取最新的MACD值
        latest_macd = macd_values.iloc[-1]
        
        rows.append({
            "代码": code, 
            "支撑因子": support_factor,
            f"MACD绝对值和_{macd_window}日": macd_abs_sum,
            "最新MACD": latest_macd,
        })
    
    return pd.DataFrame(rows)


# Configuration
DEFAULT_MACD_WINDOW = 10

def compute_support_with_default_window(history: Dict[str, pd.DataFrame], top_spot: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Wrapper function that uses the default MACD window size"""
    result = compute_support(history, top_spot, DEFAULT_MACD_WINDOW)
    
    # Rename the dynamic column to a fixed name for the factor definition
    dynamic_col = f"MACD绝对值和_{DEFAULT_MACD_WINDOW}日"
    if dynamic_col in result.columns:
        result = result.rename(columns={dynamic_col: "MACD绝对值和"})
    
    return result

SUPPORT_FACTOR = Factor(
    id="support",
    name="支撑因子",
    description=f"基于MACD绝对值总和的支撑强度：计算近{DEFAULT_MACD_WINDOW}个交易日MACD绝对值总和，总和越小表示价格波动趋于平稳，支撑越强，值越大越好",
    columns=[
        {"key": "支撑因子", "label": "支撑因子", "type": "number", "sortable": True},
        {"key": "MACD绝对值和", "label": f"{DEFAULT_MACD_WINDOW}日MACD绝对值和", "type": "number", "sortable": True},
        {"key": "最新MACD", "label": "最新MACD", "type": "number", "sortable": True},
    ],
    compute=lambda history, top_spot=None: compute_support_with_default_window(history, top_spot),
)

MODULE_FACTORS = [SUPPORT_FACTOR]
