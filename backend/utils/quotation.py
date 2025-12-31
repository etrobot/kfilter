"""
K线数据获取模块
提供腾讯证券多周期K线数据获取功能
"""

import logging
from datetime import datetime as dt
from typing import Optional

import pandas as pd
import requests
import json

logger = logging.getLogger(__name__)


def stock_zh_a_hist_tx_period(
    symbol: str = "sz000001",
    period: str = "daily",
    start_date: str = "19000101",
    end_date: str = "20500101",
    adjust: str = "",
    timeout: Optional[float] = None,
) -> pd.DataFrame:
    """
    腾讯证券-多周期-股票历史数据
    https://gu.qq.com/sh000919/zs
    :param symbol: 带市场标识的股票或者指数代码
    :param period: 周期类型 {"daily": 日线, "weekly": 周线, "monthly": 月线}
    :param start_date: 开始日期 YYYYMMDD 或 YYYY-MM-DD
    :param end_date: 结束日期 YYYYMMDD 或 YYYY-MM-DD
    :param adjust: {"qfq": 前复权, "hfq": 后复权, "": 不复权}
    :param timeout: 请求超时秒数
    :return: DataFrame: [date, open, close, high, low, amount]
    """
    # Normalize dates to YYYYMMDD
    def norm_date(s: str) -> str:
        return s.replace("-", "") if s else s

    start_date_n = norm_date(start_date)
    end_date_n = norm_date(end_date)

    # 周期映射
    period_mapping = {
        "daily": ("day", "kline_day{adjust}{year}", "{symbol},day,{year}-01-01,{year + 1}-12-31,640,{adjust}"),
        "weekly": ("week", "kline_week{adjust}", "{symbol},week,,,320,{adjust}"),
        "monthly": ("month", "kline_month{adjust}", "{symbol},month,,,320,{adjust}")
    }
    
    if period not in period_mapping:
        raise ValueError(f"不支持的周期类型: {period}，支持的类型: {list(period_mapping.keys())}")
    
    period_key, var_pattern, param_pattern = period_mapping[period]
    url = "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get"
    
    # 日线需要按年份循环获取
    if period == "daily":
        # Determine year range
        try:
            range_start = int(start_date_n[:4])
        except Exception:
            range_start = 1900
        try:
            end_year = int(end_date_n[:4])
        except Exception:
            end_year = dt.date.today().year

        current_year = dt.date.today().year
        range_end = min(end_year, current_year) + 1

        big_df = pd.DataFrame()

        for year in range(range_start, range_end):
            params = {
                "_var": var_pattern.format(adjust=adjust, year=year),
                "param": param_pattern.format(symbol=symbol, year=year, adjust=adjust),
                "r": "0.8205512681390605",
            }
            try:
                r = requests.get(url, params=params, timeout=timeout)
                r.raise_for_status()
                data_text = r.text
                idx = data_text.find("={")
                if idx == -1:
                    continue
                json_str = data_text[idx + 1:]
                json_str = json_str.strip().rstrip(";")
                data_json = json.loads(json_str).get("data", {}).get(symbol, {})

                if not data_json:
                    continue

                # 根据复权类型选择数据
                if adjust == "hfq" and "hfqday" in data_json:
                    tmp = pd.DataFrame(data_json["hfqday"])
                elif adjust == "qfq" and "qfqday" in data_json:
                    tmp = pd.DataFrame(data_json["qfqday"])
                elif "day" in data_json:
                    tmp = pd.DataFrame(data_json["day"])
                else:
                    key = next((k for k in ["qfqday", "hfqday", "day"] if k in data_json), None)
                    tmp = pd.DataFrame(data_json[key]) if key else pd.DataFrame()

                if not tmp.empty:
                    big_df = pd.concat([big_df, tmp], ignore_index=True)
            except Exception as e:
                logger.warning(f"获取{year}年日线数据失败: {symbol}, 错误: {e}")
                continue

        if big_df.empty:
            return pd.DataFrame()

        big_df = big_df.iloc[:, :6]
        big_df.columns = ["date", "open", "close", "high", "low", "amount"]

        big_df["date"] = pd.to_datetime(big_df["date"], errors="coerce").dt.date
        big_df["open"] = pd.to_numeric(big_df["open"], errors="coerce")
        big_df["close"] = pd.to_numeric(big_df["close"], errors="coerce")
        big_df["high"] = pd.to_numeric(big_df["high"], errors="coerce")
        big_df["low"] = pd.to_numeric(big_df["low"], errors="coerce")
        big_df["amount"] = pd.to_numeric(big_df["amount"], errors="coerce")
        big_df.drop_duplicates(inplace=True, ignore_index=True)

        big_df.index = pd.to_datetime(big_df["date"])  # index for slicing
        sd = pd.to_datetime(start_date_n)
        ed = pd.to_datetime(end_date_n)
        big_df = big_df.loc[sd:ed]
        big_df.reset_index(inplace=True, drop=True)

        return big_df
    
    # 周线和月线一次性获取
    else:
        # 构建请求参数
        params = {
            "_var": var_pattern.format(adjust=adjust),
            "param": param_pattern.format(symbol=symbol, adjust=adjust),
            "r": "0.29287884480018567" if period == "weekly" else "0.2325567257403376",
        }
        
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            data_text = r.text
            
            # 解析响应数据
            idx = data_text.find("={")
            if idx == -1:
                return pd.DataFrame()
                
            json_str = data_text[idx + 1:]
            json_str = json_str.strip().rstrip(";")
            data_json = json.loads(json_str).get("data", {}).get(symbol, {})
            
            if not data_json:
                return pd.DataFrame()
            
            # 根据复权类型和周期选择数据
            if adjust == "hfq":
                data_key = f"hfq{period_key}"
            elif adjust == "qfq":
                data_key = f"qfq{period_key}"
            else:
                data_key = period_key
            
            if data_key in data_json:
                data_array = data_json[data_key]
            else:
                # 自动选择可用的数据类型
                for key in [f"qfq{period_key}", f"hfq{period_key}", period_key]:
                    if key in data_json:
                        data_array = data_json[key]
                        break
                else:
                    return pd.DataFrame()
            
            if not data_array:
                return pd.DataFrame()
            
            # 创建DataFrame
            df = pd.DataFrame(data_array)
            
            # 只取前6列：date, open, close, high, low, amount
            df = df.iloc[:, :6]
            df.columns = ["date", "open", "close", "high", "low", "amount"]
            
            # 数据类型转换
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
            df["open"] = pd.to_numeric(df["open"], errors="coerce")
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df["high"] = pd.to_numeric(df["high"], errors="coerce")
            df["low"] = pd.to_numeric(df["low"], errors="coerce")
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
            
            # 去重并按日期排序
            df.drop_duplicates(inplace=True, ignore_index=True)
            df = df.sort_values("date").reset_index(drop=True)
            
            # 按日期范围过滤
            if start_date_n and end_date_n:
                start_dt = pd.to_datetime(start_date_n)
                end_dt = pd.to_datetime(end_date_n)
                df = df[(pd.to_datetime(df["date"]) >= start_dt) & (pd.to_datetime(df["date"]) <= end_dt)]
            
            return df.reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"获取{period}K数据失败: {symbol}, 错误: {e}")
            return pd.DataFrame()


def fetch_hot_spot() -> pd.DataFrame:
    """Fetch real-time stock spot data"""
    import requests
    import pandas as pd
    import json
    import re

    """
    东方财富网-沪深京 A 股-实时行情（每页100条）
    基于新的API接口获取前两页数据
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
    
    base_params = {
        'np': '1',
        'fltt': '1', 
        'invt': '2',
        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048',
        'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f23',
        'fid': 'f6',
        'pz': '100',  # 每页100条
        'po': '1',
        'dect': '1',
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'wbp2u': '|0|0|0|web',
    }
    
    all_data = []
    
    # 获取前两页数据
    for page in [1, 2]:
        params = base_params.copy()
        params['pn'] = str(page)
        
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
        
        # 收集数据
        page_data = data_json['data']['diff']
        if page_data:
            all_data.extend(page_data)
    
    # 创建DataFrame
    if not all_data:
        print("警告：获取到的数据为空")
        return pd.DataFrame()
    
    temp_df = pd.DataFrame(all_data)
    
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
    temp_df.reset_index(drop=True, inplace=True)
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
