from __future__ import annotations

import logging
from typing import Dict

import pandas as pd
import requests

logger = logging.getLogger(__name__)


def uplimit10jqka(date: str = "") -> pd.DataFrame:
    """
    从同花顺 10jqka 接口获取涨停池数据。

    返回包含以下列的 DataFrame（接口返回字段的一个子集）：
      code: 股票代码（六位字符串）
      limit_up_type: 涨停类型，文本，如："换手板" / "T字板" / "一字板"

    其他原始字段会原样返回在 DataFrame 中，便于后续扩展：
      ['open_num', 'first_limit_up_time', 'last_limit_up_time', 'code',
       'limit_up_type', 'order_volume', 'is_new', 'limit_up_suc_rate',
       'currency_value', 'market_id', 'is_again_limit', 'change_rate',
       'turnover_rate', 'reason_type', 'order_amount', 'high_days', 'name',
       'high_days_value', 'change_tag', 'market_type', 'latest', 'time_preview']

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
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5',
        'priority': 'u=1, i',
        'referer': 'https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html?client_userid=nM9Y3&back_source=hyperlink&share_hxapp=isc&fontzoom=no',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    }

    try:
        resp = requests.get(
            f'https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page=1&limit=200&field=199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004&filter=HS,GEM2STAR&date={date}&order_field=330324&order_type=0',
            cookies=cookies,
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
        info = payload.get('data', {}).get('info', []) or []
        df = pd.DataFrame(info)
        return df
    except Exception as e:
        logger.warning(f"Failed to fetch 10jqka limit-up data for date={date}: {e}")
        # 返回空DataFrame，调用方据此降级处理
        return pd.DataFrame()


def build_limit_up_map(df: pd.DataFrame) -> Dict[str, str]:
    """将 10jqka 返回的数据转换为 {code: limit_up_type} 的映射。"""
    if df is None or df.empty:
        return {}
    # 防御性处理：标准化列名
    cols = {c.lower(): c for c in df.columns}
    code_col = cols.get('code') or 'code'
    type_col = cols.get('limit_up_type') or 'limit_up_type'

    mapping: Dict[str, str] = {}
    for _, row in df.iterrows():
        code = str(row.get(code_col, '')).strip()
        lut = str(row.get(type_col, '')).strip() or None
        if code and lut:
            mapping[code] = lut
    return mapping
