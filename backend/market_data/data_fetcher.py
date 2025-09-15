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


def fetch_hot_spot() -> pd.DataFrame:
    """Fetch real-time stock spot data"""
    import requests
    import pandas as pd
    import json
    import re

    """
    东方财富网-沪深京 A 股-实时行情（单页100条）
    基于新的API接口获取第一页数据
    :return: 实时行情数据
    :rtype: pandas.DataFrame
    """
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
        'Connection': 'keep-alive',
        'Referer': 'https://quote.eastmoney.com/center/gridlist.html',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    }
    
    params = {
        'np': '1',
        'fltt': '1', 
        'invt': '2',
        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048',
        'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f23',
        'fid': 'f6',
        'pn': '1',  # 第一页
        'pz': '100',  # 每页100条
        'po': '1',
        'dect': '1',
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'wbp2u': '|0|0|0|web',
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=15)
    response.raise_for_status()
    
    # 获取响应文本
    response_text = response.text
    
    # 如果响应是JSONP格式，需要提取JSON部分
    if response_text.startswith('jQuery'):
        # 提取JSON数据（去掉JSONP回调函数包装）
        json_match = re.search(r'jQuery\w+\((.*)\)', response_text)
        if json_match:
            json_str = json_match.group(1)
            data_json = json.loads(json_str)
        else:
            raise ValueError("无法解析JSONP响应")
    else:
        # 直接解析JSON
        data_json = response.json()
    
    # 检查数据结构
    if 'data' not in data_json or 'diff' not in data_json['data']:
        raise ValueError("API返回数据结构不正确")
    
    # 创建DataFrame
    temp_df = pd.DataFrame(data_json['data']['diff'])
    
    if temp_df.empty:
        print("警告：获取到的数据为空")
        return pd.DataFrame()
    
    # 根据fields字段顺序设置列名
    # fields: f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f23
    column_mapping = {
        'f12': '代码',
        'f13': '市场',
        'f14': '名称', 
        'f1': '预期值',
        'f2': '最新价',
        'f4': '涨跌额',
        'f3': '涨跌幅',
        'f152': '市盈率TTM',
        'f5': '成交量',
        'f6': '成交额',
        'f7': '振幅',
        'f15': '最高',
        'f18': '昨收',
        'f16': '最低',
        'f17': '今开',
        'f10': '量比',
        'f8': '换手率',
        'f9': '市盈率动态',
        'f23': '市净率'
    }
    
    # 重命名列
    temp_df.rename(columns=column_mapping, inplace=True)
    
    # 添加序号列
    temp_df.reset_index(inplace=True)
    temp_df['序号'] = temp_df.index + 1
    
    # 选择需要的列并重新排序
    columns_order = [
        '序号', '代码', '名称', '最新价', '涨跌幅', '涨跌额', 
        '成交量', '成交额', '振幅', '最高', '最低', '今开', '昨收',
        '量比', '换手率', '市盈率动态', '市盈率TTM', '市净率'
    ]
    
    # 只保留存在的列
    available_columns = [col for col in columns_order if col in temp_df.columns]
    temp_df = temp_df[available_columns]
    
    # 数据类型转换
    numeric_columns = [
        '最新价', '涨跌幅', '涨跌额', '成交量', '成交额', '振幅',
        '最高', '最低', '今开', '昨收', '量比', '换手率',
        '市盈率动态', '市盈率TTM', '市净率'
    ]
    
    for col in numeric_columns:
        if col in temp_df.columns:
            temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')
    
    return temp_df




def fetch_history(codes: List[str], end_date: str, days: int = 60, task_id: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """Fetch historical data for multiple stocks"""
    if not HAS_AKSHARE:
        raise RuntimeError("akshare is not available. Please install akshare to use this feature.")
    
    history: Dict[str, pd.DataFrame] = {}
    start_date = (datetime.strptime(end_date, "%Y%m%d") - timedelta(days=days)).strftime("%Y%m%d")
    
    logger.info(f"Fetching historical data for {len(codes)} stocks from {start_date} to {end_date}")
    
    for i, code in enumerate(codes):
        # Update progress
        if task_id:
            progress = 0.2 + (0.5 * i / len(codes))  # 20%-70% of total progress
            update_task_progress(task_id, progress, f"获取历史数据 {i+1}/{len(codes)}: {code}")
        
        # Clean code - remove market prefix if it exists (e.g., sz301550 -> 301550)
        clean_code = code[2:] if len(code) > 6 and code[:2] in ['sz', 'sh', 'bj'] else code
        
        # Use the more reliable historical data interface
        df = ak.stock_zh_a_hist(symbol=clean_code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        
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


def compute_factors(top_spot: pd.DataFrame, history: Dict[str, pd.DataFrame], task_id: Optional[str] = None, selected_factors: Optional[List[str]] = None) -> pd.DataFrame:
    """Compute comprehensive factors for stock analysis via pluggable factor modules"""
    from factors import compute_all_factors, compute_selected_factors

    logger.info("Computing factors using modular plugins...")

    if task_id:
        update_task_progress(task_id, 0.7, "计算各类因子")

    # Filter history to only include top stocks
    filtered_history = {code: df for code, df in history.items() if code in top_spot["代码"].values}

    # Compute selected or all registered factor dataframes
    if selected_factors:
        factors_df = compute_selected_factors(filtered_history, top_spot, selected_factors)
        logger.info(f"Computing selected factors: {selected_factors}")
    else:
        factors_df = compute_all_factors(filtered_history, top_spot)
        logger.info("Computing all available factors")

    if factors_df is None or factors_df.empty:
        logger.warning("No factor data calculated")
        # Still return basic info if available
        factors_df = pd.DataFrame({"代码": list(filtered_history.keys())})

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

    result = factors_df

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

    # Generic score computation: for any column ending with '因子', compute a percentile rank score with suffix '评分'
    score_columns = []
    for col in list(result.columns):
        if isinstance(col, str) and col.endswith("因子"):
            score_col = col.replace("因子", "评分")
            try:
                result[score_col] = result[col].rank(ascending=True, pct=True)
                score_columns.append(score_col)
            except Exception:
                # ignore non-numeric
                pass

    # Composite score: average of all available score columns if any
    if score_columns:
        result["综合评分"] = result[score_columns].mean(axis=1)
        result = result.sort_values("综合评分", ascending=False)

    if task_id:
        update_task_progress(task_id, 0.9, "计算因子评分")

    logger.info(f"Calculated factors for {len(result)} stocks with 换手板 counts")
    return result

def fetch_dragon_tiger_data(page_number: int = 1, page_size: int = 50, statistics_cycle: str = "04") -> pd.DataFrame:
    """
    获取东方财富网龙虎榜数据
    
    Parameters:
    - page_number: 页码，默认第1页
    - page_size: 每页数据量，默认50条  
    - statistics_cycle: 统计周期，"04"表示近一年
    
    Returns:
    - pandas.DataFrame: 龙虎榜数据
    """
    import requests
    import pandas as pd
    import json
    import re
    import time
    
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
        'Connection': 'keep-alive',
        'Referer': 'https://data.eastmoney.com/stock/stockstatistic.html',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    }
    
    # 生成回调函数名（模拟jQuery）
    callback_name = f"jQuery{int(time.time() * 1000)}_{int(time.time() * 1000000)}"
    
    params = {
        'callback': callback_name,
        'sortColumns': 'BILLBOARD_TIMES,LATEST_TDATE,SECURITY_CODE',
        'sortTypes': '-1,-1,1',
        'pageSize': str(page_size),
        'pageNumber': str(page_number),
        'reportName': 'RPT_BILLBOARD_TRADEALLNEW',
        'columns': 'ALL',
        'source': 'WEB',
        'client': 'WEB',
        'filter': f'(STATISTICS_CYCLE="{statistics_cycle}")'
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=15)
    response.raise_for_status()
    
    # 获取响应文本
    response_text = response.text
    
    # 解析JSONP响应
    if response_text.startswith(callback_name):
        # 提取JSON数据（去掉JSONP回调函数包装）
        json_match = re.search(r'\((.*)\)', response_text)
        if json_match:
            json_str = json_match.group(1)
            data_json = json.loads(json_str)
        else:
            raise ValueError("无法解析JSONP响应")
    else:
        # 直接解析JSON
        data_json = response.json()
    
    # 检查数据结构
    if 'result' not in data_json or 'data' not in data_json['result']:
        raise ValueError("API返回数据结构不正确")
    
    # 创建DataFrame
    temp_df = pd.DataFrame(data_json['result']['data'])
    
    if temp_df.empty:
        print("警告：获取到的数据为空")
        return pd.DataFrame()
    
    # 定义列名映射
    column_mapping = {
        'SECURITY_CODE': '代码',
        'SECURITY_NAME_ABBR': '名称',
        'LATEST_TDATE': '最近上榜日',
        'CLOSE_PRICE': '收盘价',
        'CHANGE_RATE': '涨跌幅',
        'BILLBOARD_TIMES': '上榜次数',
        'BILLBOARD_NET_BUY': '龙虎榜净买额',
        'BILLBOARD_BUY_AMT': '龙虎榜买入额',
        'BILLBOARD_SELL_AMT': '龙虎榜卖出额',
        'BILLBOARD_DEAL_AMT': '龙虎榜总成交额',
        'ORG_BUY_TIMES': '买方机构次数',
        'ORG_SELL_TIMES': '卖方机构次数',
        'ORG_NET_BUY': '机构买入净额',
        'ORG_BUY_AMT': '机构买入总额',
        'ORG_SELL_AMT': '机构卖出总额',
        'IPCT1M': '近1个月涨跌幅',
        'IPCT3M': '近3个月涨跌幅',
        'IPCT6M': '近6个月涨跌幅',
        'IPCT1Y': '近1年涨跌幅'
    }
    
    # 重命名列
    temp_df.rename(columns=column_mapping, inplace=True)
    
    # 过滤退市和ST股票
    if '名称' in temp_df.columns:
        # 去掉名字以"退市"开头的股票
        temp_df = temp_df[~temp_df['名称'].str.startswith('退市', na=False)]
        # 去掉名字以"*ST"开头的股票
        temp_df = temp_df[~temp_df['名称'].str.startswith('*ST', na=False)]
    
    # 添加序号列
    temp_df.reset_index(drop=True, inplace=True)
    temp_df['序号'] = temp_df.index + 1
    
    # 选择需要的列并重新排序
    columns_order = [
        '序号', '代码', '名称', '最近上榜日', '收盘价', '涨跌幅', '上榜次数',
        '龙虎榜净买额', '龙虎榜买入额', '龙虎榜卖出额', '龙虎榜总成交额',
        '买方机构次数', '卖方机构次数', '机构买入净额', '机构买入总额', '机构卖出总额',
        '近1个月涨跌幅', '近3个月涨跌幅', '近6个月涨跌幅', '近1年涨跌幅'
    ]
    
    # 只保留存在的列
    available_columns = [col for col in columns_order if col in temp_df.columns]
    temp_df = temp_df[available_columns]
    
    # 数据格式化
    # 处理日期格式
    if '最近上榜日' in temp_df.columns:
        temp_df['最近上榜日'] = pd.to_datetime(temp_df['最近上榜日']).dt.strftime('%Y-%m-%d')
    
    # 转换金额单位（从元转为万元）
    money_columns = [
        '龙虎榜净买额', '龙虎榜买入额', '龙虎榜卖出额', '龙虎榜总成交额',
        '机构买入净额', '机构买入总额', '机构卖出总额'
    ]
    
    for col in money_columns:
        if col in temp_df.columns:
            temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce') / 10000
            temp_df[col] = temp_df[col].round(2)
    
    # 数值型列处理
    numeric_columns = [
        '收盘价', '涨跌幅', '上榜次数', '买方机构次数', '卖方机构次数',
        '近1个月涨跌幅', '近3个月涨跌幅', '近6个月涨跌幅', '近1年涨跌幅'
    ] + money_columns
    
    for col in numeric_columns:
        if col in temp_df.columns:
            if col not in money_columns:  # 金额列已经处理过了
                temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')
            if col in ['涨跌幅', '近1个月涨跌幅', '近3个月涨跌幅', '近6个月涨跌幅', '近1年涨跌幅']:
                temp_df[col] = temp_df[col].round(2)
    
    return temp_df