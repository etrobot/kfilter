from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from task_utils import update_task_progress
import datetime as dt
from utils.quotation import stock_zh_a_hist_tx_period

# Try to import akshare, handle gracefully if not available
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    ak = None

logger = logging.getLogger(__name__)


def fetch_history(codes: List[str], end_date: str, days: int = 60, task_id: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """Fetch historical data for multiple stocks"""
    history: Dict[str, pd.DataFrame] = {}
    start_date = (datetime.strptime(end_date, "%Y%m%d") - timedelta(days=days)).strftime("%Y%m%d")
    
    logger.info(f"Fetching historical data for {len(codes)} stocks from {start_date} to {end_date}")
    
    for i, code in enumerate(codes):
        # Update progress
        if task_id:
            progress = 0.2 + (0.5 * i / len(codes))  # 20%-70% of total progress
            update_task_progress(task_id, progress, f"获取历史数据 {i+1}/{len(codes)}: {code}")
        
        # Prefer akshare, fallback to Tencent if akshare fails or returns empty
        def to_symbol(c: str) -> str:
            c = c.strip()
            if len(c) == 6 and c.isdigit():
                if c.startswith("6"):
                    return f"sh{c}"
                if c.startswith(("0", "3")):
                    return f"sz{c}"
                if c.startswith("8"):
                    return f"bj{c}"
            return c

        def to_clean_code(c: str) -> str:
            c = c.strip()
            if len(c) > 6 and c[:2] in ["sh", "sz", "bj"]:
                return c[2:]
            return c

        df = pd.DataFrame()
        # 1) Try akshare's general interface first (has more complete data including 成交额)
        if HAS_AKSHARE:
            try:
                ak_code = to_clean_code(code)
                df = ak.stock_zh_a_hist(symbol=ak_code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            except Exception as e:
                logger.warning(f"akshare通用接口获取异常，尝试akshare腾讯接口: {code}, 错误: {e}")
                df = pd.DataFrame()

        # 2) Fallback to akshare's Tencent API (less data but more stable)
        if (df is None or df.empty) and HAS_AKSHARE:
            try:
                api_symbol = to_symbol(code)
                df = ak.stock_zh_a_hist_tx(symbol=api_symbol, start_date=start_date, end_date=end_date, adjust="qfq")
            except Exception as e:
                logger.warning(f"akshare腾讯接口也获取异常，将尝试本地腾讯实现: {code}, 错误: {e}")
                df = pd.DataFrame()

        # 3) Final fallback to local Tencent implementation
        if df is None or df.empty:
            try:
                api_symbol = to_symbol(code)
                df = stock_zh_a_hist_tx_period(symbol=api_symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            except Exception as e:
                logger.warning(f"本地腾讯实现也失败: {code}, 错误: {e}")
                df = pd.DataFrame()

        if df is None or df.empty:
            logger.warning(f"三种方式均未获取到数据: {code}")
            continue
        
        if not df.empty:
            # Standardize column names
            df = df.reset_index(drop=True)
            
            # Handle different API formats
            # Tencent API returns: date, open, close, high, low, amount (成交量 only)
            # General API returns: 日期, 股票代码, 开盘, 收盘, 最高, 最低, 成交量, 成交额, etc.
            rename_map = {
                "date": "日期",
                "open": "开盘",
                "close": "收盘",
                "high": "最高",
                "low": "最低",
                "amount": "成交量",  # Tencent API's amount is volume, not turnover
                "股票代码": "代码",
            }
            existing_columns = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_columns)
            
            # Ensure date column is datetime
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"])
            
            # Convert numeric columns
            numeric_columns = ["开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Compute missing percentage change if not provided
            if "涨跌幅" not in df.columns and "收盘" in df.columns:
                df["涨跌幅"] = df["收盘"].pct_change() * 100
            
            # Set stock code
            if "代码" not in df.columns:
                df["代码"] = code
            
            history[code] = df
            
            if (i + 1) % 50 == 0:
                logger.info(f"Processed {i + 1}/{len(codes)} stocks")
    
    logger.info(f"Successfully fetched historical data for {len(history)} stocks")
    return history

def compute_factors(top_spot: pd.DataFrame, history: Dict[str, pd.DataFrame], task_id: Optional[str] = None, selected_factors: Optional[List[str]] = None) -> pd.DataFrame:
    """Compute comprehensive factors for stock analysis via pluggable factor modules"""
    from factors import compute_all_factors, compute_selected_factors

    logger.info("Computing factors using modular plugins...")

    if task_id:
        update_task_progress(task_id, 0.7, "计算各类因子")

    # Filter history to only include top stocks
    logger.info(f"开始因子计算：输入history包含 {len(history)} 个股票")
    logger.info(f"top_spot包含 {len(top_spot)} 个股票")
    filtered_history = {code: df for code, df in history.items() if code in top_spot["代码"].values}
    logger.info(f"过滤后的history包含 {len(filtered_history)} 个股票")
    logger.info(f"过滤后的股票代码：{list(filtered_history.keys())[:10]}{'...' if len(filtered_history) > 10 else ''}")

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
    else:
        logger.info(f"因子计算完成，返回 {len(factors_df)} 个股票的因子数据")

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

    logger.info(f"最终结果包含 {len(result)} 个股票")
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
        # 去掉名字以"退"结尾的股票
        temp_df = temp_df[~temp_df['名称'].str.endswith('退', na=False)]
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