#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

import pandas as pd
from factors.support import days_from_longest_candle, compute_support

# Test the days_from_longest_candle function
test_candles = [
    {'open': 10, 'close': 10.5, 'high': 11, 'low': 9.5},  # body = 0.5
    {'open': 11, 'close': 10, 'high': 11.5, 'low': 9.8},   # body = 1.0 (largest)
    {'open': 10, 'close': 10.2, 'high': 10.8, 'low': 9.9}, # body = 0.2
    {'open': 10.2, 'close': 10.8, 'high': 11.2, 'low': 10}, # body = 0.6
]

days = days_from_longest_candle(test_candles, 4)
print(f'Days from longest candle: {days}')
print('Expected: 2 (index 1 is largest, so 4-1-1=2)')

# Test with sample DataFrame
test_df = pd.DataFrame({
    '日期': pd.date_range('2024-01-01', periods=25),
    '开盘': [10 + i*0.1 for i in range(25)],
    '收盘': [10.5 + i*0.1 + (0.5 if i == 5 else 0.1) for i in range(25)],  # Day 5 has largest body
    '最高': [11 + i*0.1 for i in range(25)],
    '最低': [9.5 + i*0.1 for i in range(25)]
})

history = {'TEST001': test_df}
result = compute_support(history)
print('\nSupport factor result:')
print(result)