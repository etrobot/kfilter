from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from utils import update_task_progress

# Try to import akshare, handle gracefully if not available
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    ak = None

logger = logging.getLogger(__name__)


def fetch_spot() -> pd.DataFrame:
    """Fetch real-time stock spot data"""
    if not HAS_AKSHARE:
        raise RuntimeError("akshare is not available. Please install akshare to use this feature.")
    
    logger.info("Fetching real-time spot data from akshare...")
    df = ak.stock_zh_a_spot_em()
    
    # Standardize column names
    column_mapping = {
        "代码": "代码",
        "名称": "名称", 
        "最新价": "最新价",
        "涨跌幅": "涨跌幅",
        "涨跌额": "涨跌额",
        "成交量": "成交量",
        "成交额": "成交额",
        "振幅": "振幅",
        "最高": "最高",
        "最低": "最低",
        "今开": "今开",
        "昨收": "昨收"
    }
    
    # Rename columns if they exist
    existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
    df = df.rename(columns=existing_columns)
    
    # Convert numeric columns
    numeric_columns = ["最新价", "涨跌幅", "涨跌额", "成交量", "成交额", "振幅", "最高", "最低", "今开", "昨收"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Sort by trading volume (成交额)
    if "成交额" in df.columns:
        df = df.sort_values("成交额", ascending=False)
    
    logger.info(f"Successfully fetched {len(df)} stocks from spot data")
    return df


def fetch_history(codes: List[str], days: int = 60, task_id: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """Fetch historical data for multiple stocks"""
    if not HAS_AKSHARE:
        raise RuntimeError("akshare is not available. Please install akshare to use this feature.")
    
    history: Dict[str, pd.DataFrame] = {}
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    
    logger.info(f"Fetching historical data for {len(codes)} stocks from {start_date} to {end_date}")
    
    for i, code in enumerate(codes):
        # Update progress
        if task_id:
            progress = 0.2 + (0.5 * i / len(codes))  # 20%-70% of total progress
            update_task_progress(task_id, progress, f"获取历史数据 {i+1}/{len(codes)}: {code}")
        
        # Use the more reliable historical data interface
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        
        if not df.empty:
            # Standardize column names
            df = df.reset_index()
            column_mapping = {
                "日期": "日期",
                "开盘": "开盘",
                "收盘": "收盘", 
                "最高": "最高",
                "最低": "最低",
                "成交量": "成交量",
                "成交额": "成交额",
                "振幅": "振幅",
                "涨跌幅": "涨跌幅",
                "涨跌额": "涨跌额",
                "换手率": "换手率"
            }
            
            # Rename existing columns
            existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing_columns)
            
            # Ensure date column is datetime
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"])
            
            # Convert numeric columns
            numeric_columns = ["开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df["代码"] = code
            history[code] = df
            
            if (i + 1) % 50 == 0:
                logger.info(f"Processed {i + 1}/{len(codes)} stocks")
    
    logger.info(f"Successfully fetched historical data for {len(history)} stocks")
    return history


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


def compute_factors(top_spot: pd.DataFrame, history: Dict[str, pd.DataFrame], task_id: Optional[str] = None) -> pd.DataFrame:
    """Compute comprehensive factors for stock analysis"""
    logger.info("Computing momentum and support factors...")
    
    if task_id:
        update_task_progress(task_id, 0.7, "计算动量因子和支撑因子")
    
    # Filter history to only include top stocks
    filtered_history = {code: df for code, df in history.items() if code in top_spot["代码"].values}
    
    # Calculate individual factors
    momentum_df = calculate_momentum_factor(filtered_history, period=20)
    support_df = calculate_support_factor(filtered_history, period=5)

    # Calculate count of '换手板' occurrences within the analysis window
    hs_counts = []
    for code, df in filtered_history.items():
        count = 0
        if df is not None and not df.empty and "limit_up_text" in df.columns:
            try:
                count = int((df["limit_up_text"].fillna("") == "换手板").sum())
            except Exception:
                count = 0
        hs_counts.append({"代码": code, "换手板": count})
    hs_counts_df = pd.DataFrame(hs_counts)
    
    if momentum_df.empty and support_df.empty:
        logger.warning("No factor data calculated")
        return pd.DataFrame()
    
    # Merge factors
    result = momentum_df.merge(support_df, on="代码", how="outer")
    
    # Merge '换手板' counts
    if not hs_counts_df.empty:
        result = result.merge(hs_counts_df, on="代码", how="left")
    
    # Add current price, stock name and other basic info
    current_data = []
    for code in result["代码"].tolist():
        df = filtered_history.get(code)
        if df is not None and not df.empty:
            df_sorted = df.sort_values("日期")
            # Get stock name from top_spot data
            stock_name = top_spot[top_spot["代码"] == code]["名称"].iloc[0] if "名称" in top_spot.columns and len(top_spot[top_spot["代码"] == code]) > 0 else code
            current_data.append({
                "代码": code,
                "名称": stock_name,
                "当前价格": float(df_sorted["收盘"].iloc[-1]),
                "涨跌幅": float(df_sorted["涨跌幅"].iloc[-1]) if "涨跌幅" in df_sorted.columns else 0
            })
    
    current_df = pd.DataFrame(current_data)
    if not current_df.empty:
        result = result.merge(current_df, on="代码", how="left")
    
    # Calculate factor scores (percentile ranking)
    if "动量因子" in result.columns:
        result["动量评分"] = result["动量因子"].rank(ascending=True, pct=True)
    
    if "支撑因子" in result.columns:
        result["支撑评分"] = result["支撑因子"].rank(ascending=True, pct=True)
    
    # Calculate composite score
    if "动量评分" in result.columns and "支撑评分" in result.columns:
        result["综合评分"] = (result["动量评分"] * 0.6 + result["支撑评分"] * 0.4)
        result = result.sort_values("综合评分", ascending=False)
    
    if task_id:
        update_task_progress(task_id, 0.9, "计算因子评分")
    
    logger.info(f"Calculated factors for {len(result)} stocks with 换手板 counts")
    return result