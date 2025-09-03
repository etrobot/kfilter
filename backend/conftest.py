import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def spot_data():
    """Mocked real-time spot data used by tests"""
    df = pd.DataFrame({
        '代码': ['000001', '000002', '600000', '600036', '000858'],
        '名称': ['平安银行', '万科A', '浦发银行', '招商银行', '五粮液'],
        '最新价': [10.50, 8.75, 9.20, 38.50, 180.20],
        '涨跌幅': [2.15, -1.20, 0.80, 1.50, -0.75],
        '涨跌额': [0.22, -0.11, 0.07, 0.57, -1.36],
        '成交量': [1250000, 980000, 1100000, 850000, 420000],
        '成交额': [13125000, 8575000, 10120000, 32725000, 75684000],
        '今开': [10.30, 8.90, 9.15, 38.00, 181.50],
        '最高': [10.60, 8.95, 9.25, 38.80, 182.00],
        '最低': [10.20, 8.70, 9.10, 37.90, 179.50],
        '昨收': [10.28, 8.86, 9.13, 37.93, 181.56]
    })
    return df


@pytest.fixture
def history_data():
    """Mocked historical daily data per code used by tests"""
    dates = [(datetime.now() - timedelta(days=i)).date() for i in range(10, 0, -1)]
    history = {}
    for code in ['000001', '000002', '600000', '600036', '000858']:
        data = []
        base_price = {
            '000001': 10.0,
            '000002': 8.0,
            '600000': 9.0,
            '600036': 38.0,
            '000858': 180.0,
        }[code]
        for i, d in enumerate(dates):
            price = base_price + (i * 0.1) + float(np.random.uniform(-0.2, 0.2))
            open_price = price + float(np.random.uniform(-0.1, 0.1))
            high_price = max(open_price, price) + float(np.random.uniform(0, 0.2))
            low_price = min(open_price, price) - float(np.random.uniform(0, 0.2))
            data.append({
                '日期': pd.Timestamp(d),
                '开盘': round(open_price, 2),
                '最高': round(high_price, 2),
                '最低': round(low_price, 2),
                '收盘': round(price, 2),
                '成交量': int(np.random.uniform(500000, 2000000)),
                '成交额': int(np.random.uniform(5000000, 20000000)),
                '涨跌幅': round(float(np.random.uniform(-3, 3)), 2),
            })
        history[code] = pd.DataFrame(data)
    return history


@pytest.fixture
def daily_data(history_data):
    """Alias fixture for workflow tests that expect 'daily_data'."""
    return history_data
