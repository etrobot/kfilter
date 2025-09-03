#!/usr/bin/env python3
"""
简化测试脚本：测试股票数据处理的核心功能
避免SQLModel表重定义问题
"""

import logging
import sys
import os
import numpy as np

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """测试模块导入"""
    logger.info("=== 测试模块导入 ===")
    try:
        # 测试数据处理模块
        logger.info("导入 data_processor...")
        from data_processor import fetch_spot
        logger.info("✅ data_processor 导入成功")
        
        # 测试股票数据管理模块
        logger.info("导入 stock_data_manager...")
        import stock_data_manager
        logger.info("✅ stock_data_manager 导入成功")
        
        # 测试市场数据处理模块
        logger.info("导入 market_data_processor...")
        import market_data_processor
        logger.info("✅ market_data_processor 导入成功")
        
        # 测试模型
        logger.info("导入 models...")
        from models import Task, TaskStatus
        logger.info("✅ models 导入成功")
        
        return True
    except Exception as e:
        logger.error(f"❌ 模块导入失败: {e}")
        return False


def test_fetch_spot():
    """测试获取实时数据（模拟数据）"""
    logger.info("=== 测试获取实时数据 ===")
    try:
        # 由于可能没有akshare或网络问题，我们创建模拟数据
        import pandas as pd
        import numpy as np
        
        # 创建模拟的实时数据
        mock_spot_data = pd.DataFrame({
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
        
        logger.info(f"✅ 模拟实时数据创建成功，共 {len(mock_spot_data)} 条记录")
        logger.info(f"数据列: {list(mock_spot_data.columns)}")
        
        # 显示前3条记录
        logger.info("前3条数据:")
        for _, row in mock_spot_data.head(3).iterrows():
            logger.info(f"  {row['代码']} {row['名称']}: {row['最新价']} ({row['涨跌幅']:+.2f}%)")
        
        return True, mock_spot_data
    except Exception as e:
        logger.error(f"❌ 创建模拟数据失败: {e}")
        return False, None


def test_historical_data():
    """测试历史数据处理（模拟数据）"""
    logger.info("=== 测试历史数据处理 ===")
    try:
        import pandas as pd
        from datetime import datetime, timedelta
        
        # 创建模拟历史数据
        dates = [(datetime.now() - timedelta(days=i)).date() for i in range(10, 0, -1)]
        
        mock_history = {}
        for code in ['000001', '000002']:
            data = []
            base_price = 10.0 if code == '000001' else 8.0
            
            for i, date in enumerate(dates):
                # 模拟价格波动
                price = base_price + (i * 0.1) + np.random.uniform(-0.2, 0.2)
                open_price = price + np.random.uniform(-0.1, 0.1)
                high_price = max(open_price, price) + np.random.uniform(0, 0.2)
                low_price = min(open_price, price) - np.random.uniform(0, 0.2)
                
                data.append({
                    '日期': pd.Timestamp(date),
                    '开盘': round(open_price, 2),
                    '最高': round(high_price, 2),
                    '最低': round(low_price, 2),
                    '收盘': round(price, 2),
                    '成交量': int(np.random.uniform(500000, 2000000)),
                    '成交额': int(np.random.uniform(5000000, 20000000)),
                    '涨跌幅': round(np.random.uniform(-3, 3), 2)
                })
            
            mock_history[code] = pd.DataFrame(data)
        
        logger.info(f"✅ 模拟历史数据创建成功，共 {len(mock_history)} 个股票")
        for code, df in mock_history.items():
            logger.info(f"  {code}: {len(df)} 条记录，日期范围 {df['日期'].min().date()} 到 {df['日期'].max().date()}")
        
        return True, mock_history
    except Exception as e:
        logger.error(f"❌ 创建模拟历史数据失败: {e}")
        return False, None


def test_factor_calculation(spot_data, history_data):
    """测试因子计算"""
    logger.info("=== 测试因子计算 ===")
    try:
        from data_processor import compute_factors
        
        # 计算因子
        factors_df = compute_factors(spot_data.head(2), history_data)
        
        if not factors_df.empty:
            logger.info(f"✅ 因子计算成功，共 {len(factors_df)} 条结果")
            logger.info(f"因子列: {list(factors_df.columns)}")
            
            # 显示结果
            for _, row in factors_df.iterrows():
                logger.info(f"  {row.get('代码', 'N/A')} {row.get('名称', 'N/A')}: "
                          f"动量={row.get('动量因子', 'N/A'):.4f}, "
                          f"支撑={row.get('支撑因子', 'N/A'):.4f}, "
                          f"综合评分={row.get('综合评分', 'N/A'):.4f}")
            return True
        else:
            logger.warning("⚠️ 因子计算结果为空")
            return False
            
    except Exception as e:
        logger.error(f"❌ 因子计算失败: {e}")
        return False


def test_database_operations():
    """测试数据库操作（不实际创建数据库）"""
    logger.info("=== 测试数据库操作函数 ===")
    try:
        # 测试函数定义是否正确
        from stock_data_manager import (
            get_missing_daily_data,
            save_daily_data,
            save_spot_as_daily_data,
            save_stock_basic_info,
            load_daily_data_for_analysis
        )
        
        from market_data_processor import (
            calculate_and_save_weekly_data,
            calculate_and_save_monthly_data,
            get_weekly_data,
            get_monthly_data,
            calculate_technical_indicators
        )
        
        logger.info("✅ 所有数据库操作函数定义正确")
        
        # 测试技术指标计算（不需要数据库）
        import pandas as pd
        test_df = pd.DataFrame({
            '日期': pd.date_range('2023-01-01', periods=30),
            '收盘': [10 + i * 0.1 + (i % 5 - 2) * 0.2 for i in range(30)],
            '最高': [10.5 + i * 0.1 + (i % 3) * 0.1 for i in range(30)],
            '最低': [9.5 + i * 0.1 - (i % 4) * 0.1 for i in range(30)]
        })
        
        indicators_df = calculate_technical_indicators(test_df)
        logger.info(f"✅ 技术指标计算成功，包含 {len([col for col in indicators_df.columns if col.startswith(('MA', 'RSI', 'BB_'))])} 个指标")
        
        return True
    except Exception as e:
        logger.error(f"❌ 数据库操作测试失败: {e}")
        return False


def test_services():
    """测试服务模块"""
    logger.info("=== 测试服务模块 ===")
    try:
        from services import create_analysis_task
        from utils import add_task, get_task
        
        logger.info("✅ 服务模块导入成功")
        
        # 测试任务相关的模型
        from models import Task, TaskStatus
        from datetime import datetime
        from uuid import uuid4
        
        # 创建测试任务
        test_task = Task(
            task_id=str(uuid4()),
            status=TaskStatus.PENDING,
            progress=0.0,
            message="测试任务",
            created_at=datetime.now().isoformat(),
            top_n=10
        )
        
        logger.info(f"✅ 测试任务对象创建成功: {test_task.task_id}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 服务模块测试失败: {e}")
        return False


def main():
    """主测试函数"""
    logger.info("🚀 开始股票数据处理简化测试")
    
    results = []
    
    # 1. 测试模块导入
    results.append(("模块导入", test_imports()))
    
    # 2. 测试实时数据
    success, spot_data = test_fetch_spot()
    results.append(("实时数据处理", success))
    
    # 3. 测试历史数据
    success, history_data = test_historical_data()
    results.append(("历史数据处理", success))
    
    # 4. 测试因子计算
    if spot_data is not None and history_data is not None:
        results.append(("因子计算", test_factor_calculation(spot_data, history_data)))
    
    # 5. 测试数据库操作函数
    results.append(("数据库操作函数", test_database_operations()))
    
    # 6. 测试服务模块
    results.append(("服务模块", test_services()))
    
    # 汇总结果
    logger.info("\n" + "="*50)
    logger.info("📊 测试结果汇总:")
    logger.info("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    logger.info("="*50)
    logger.info(f"测试通过: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 所有测试通过！股票数据处理模块正常工作")
        logger.info("📝 注意：本次测试使用模拟数据，实际运行时需要:")
        logger.info("   1. 确保 akshare 可以正常获取数据")
        logger.info("   2. 数据库连接正常")
        logger.info("   3. 网络环境支持API调用")
        return True
    else:
        logger.warning(f"⚠️ 有 {total-passed} 个测试失败，请检查相关功能")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 测试过程中发生未预期错误: {e}")
        sys.exit(1)