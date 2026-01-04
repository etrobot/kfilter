from __future__ import annotations

import logging
from typing import Dict

import pandas as pd
import requests

logger = logging.getLogger(__name__)


def uplimit10jqka(date: str = "") -> pd.DataFrame:
    """
    从同花顺 10jqka 接口获取涨停热门板块数据（使用 block_top 接口）。

    返回包含以下列的 DataFrame：
      code: 板块代码
      name: 板块名称
      change: 涨跌幅
      limit_up_num: 涨停数量
      continuous_plate_num: 连板数量
      high: 最高连板信息（如 "10天9板"）
      high_num: 最高连板股票代码
      days: 持续天数
      stock_list: 个股列表（list of dict），每个股票包含 code, name, limit_up_type 等信息

    参数
    - date: 字符串格式的日期，如 '2025-01-15' 或 '20250115'，为空则默认当天。
    """
    import sys
    from pathlib import Path
    # Add backend to path to import config
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    from config import THS_COOKIE_V
    cookie_v = THS_COOKIE_V
    cookies = {
        'v': cookie_v,
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Referer': 'https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html?client_userid=nM9Y3&back_source=hyperlink&share_hxapp=isc&fontzoom=no',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }

    try:
        resp = requests.get(
            f'https://data.10jqka.com.cn/dataapi/limit_up/block_top?filter=HS,GEM2STAR&date={date}',
            cookies=cookies,
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get('data', []) or []
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        logger.warning(f"Failed to fetch 10jqka block_top data for date={date}: {e}")
        # 返回空DataFrame，调用方据此降级处理
        return pd.DataFrame()


def build_limit_up_map(df: pd.DataFrame) -> Dict[str, str]:
    """
    将 10jqka block_top 接口返回的数据转换为 {code: limit_up_type} 的映射。
    
    新接口返回的是板块数据，每个板块包含 stock_list 字段，
    我们需要从 stock_list 中提取所有股票的涨停类型。
    """
    if df is None or df.empty:
        return {}
    
    mapping: Dict[str, str] = {}
    
    # 遍历每个板块
    for _, sector_row in df.iterrows():
        stock_list = sector_row.get('stock_list', [])
        if not stock_list or not isinstance(stock_list, list):
            continue
        
        # 遍历板块中的每只股票
        for stock in stock_list:
            if not isinstance(stock, dict):
                continue
            
            code = str(stock.get('code', '')).strip()
            # 尝试获取涨停类型，可能的字段名：limit_up_type, change_tag, high
            lut = None
            
            # 优先使用 limit_up_type 字段
            if 'limit_up_type' in stock:
                lut = str(stock.get('limit_up_type', '')).strip()
            # 如果没有，尝试使用 high 字段（如 "首板", "2连板"）
            elif 'high' in stock:
                lut = str(stock.get('high', '')).strip()
            # 或者使用 change_tag 字段
            elif 'change_tag' in stock:
                lut = str(stock.get('change_tag', '')).strip()
            
            if code and lut:
                mapping[code] = lut
    
    return mapping


def save_hot_sectors_to_db(df: pd.DataFrame, date_str: str = "") -> int:
    """
    将热门板块数据保存到数据库（覆盖模式）。
    先删除当天的旧数据，再插入新数据。
    
    参数:
        df: block_top_10jqka 返回的 DataFrame
        date_str: 日期字符串，如 '2025-01-15' 或 '20250115'
        
    返回:
        保存的记录数
    """
    import sys
    from pathlib import Path
    import json
    from datetime import datetime, date as dt_date
    
    # Add backend to path to import models
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    from models import DailyHotSector, get_session
    from sqlmodel import select
    
    if df is None or df.empty:
        logger.info("No hot sector data to save")
        return 0
    
    # 解析日期
    if date_str:
        try:
            # 尝试解析不同格式
            if '-' in date_str:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                target_date = datetime.strptime(date_str, '%Y%m%d').date()
        except Exception as e:
            logger.warning(f"Failed to parse date {date_str}: {e}, using today")
            target_date = dt_date.today()
    else:
        target_date = dt_date.today()
    
    saved_count = 0
    with get_session() as session:
        # 先删除当天的旧数据（覆盖模式）
        try:
            existing_records = session.exec(
                select(DailyHotSector).where(DailyHotSector.date == target_date)
            ).all()
            
            deleted_count = len(existing_records)
            if deleted_count > 0:
                for record in existing_records:
                    session.delete(record)
                session.commit()
                logger.info(f"Deleted {deleted_count} existing hot sectors for date {target_date}")
        except Exception as e:
            session.rollback()
            logger.warning(f"Failed to delete existing hot sectors: {e}")
        
        # 插入新数据
        for _, row in df.iterrows():
            try:
                # 将 stock_list 转换为 JSON 字符串
                stock_list = row.get('stock_list', [])
                stock_list_json = json.dumps(stock_list, ensure_ascii=False)
                
                # 创建记录
                hot_sector = DailyHotSector(
                    date=target_date,
                    sector_code=str(row.get('code', '')),
                    sector_name=str(row.get('name', '')),
                    change_pct=float(row.get('change', 0)),
                    limit_up_num=int(row.get('limit_up_num', 0)),
                    continuous_plate_num=int(row.get('continuous_plate_num', 0)),
                    high_info=str(row.get('high', '')) if row.get('high') else None,
                    high_num=int(row.get('high_num', 0)) if row.get('high_num') else None,
                    days=int(row.get('days', 0)) if row.get('days') else None,
                    stock_list_json=stock_list_json,
                )
                session.add(hot_sector)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Failed to save hot sector {row.get('name', 'unknown')}: {e}")
                continue
        
        try:
            session.commit()
            logger.info(f"Saved {saved_count} hot sectors for date {target_date}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to commit hot sectors: {e}")
            return 0
    
    return saved_count
