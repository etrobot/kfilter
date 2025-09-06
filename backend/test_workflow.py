#!/usr/bin/env python3
"""
测试脚本：验证股票数据处理完整流程
包括：数据库创建、数据获取、存储、K线计算、因子分析
"""

import logging
import sys
from datetime import date
import pandas as pd
import akshare as ak

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_setup():
    """测试数据库初始化"""
    logger.info("=== 测试数据库初始化 ===")
    from models import create_db_and_tables
    create_db_and_tables()
    logger.info("✅ 数据库初始化成功")
    return True


def test_fetch_spot_data():
    """测试获取实时行情数据"""
    logger.info("=== 测试获取实时行情数据 ===")
    from data_processor import fetch_spot
    spot_data = fetch_spot()
    
    if spot_data.empty:
        logger.warning("⚠️ 实时行情数据为空")
        return False, None
        
    logger.info(f"✅ 获取实时行情成功，共 {len(spot_data)} 条记录")
    logger.info(f"数据列: {list(spot_data.columns)}")
    return True, spot_data


def test_save_basic_info(spot_data):
    """测试保存股票基本信息"""
    logger.info("=== 测试保存股票基本信息 ===")
    from stock_data_manager import save_stock_basic_info
    saved_count = save_stock_basic_info(spot_data.head(10))  # 只测试前10条
    logger.info(f"✅ 保存股票基本信息成功，共 {saved_count} 条")
    return True


def test_save_spot_as_daily(spot_data):
    """测试保存实时数据为今日行情"""
    logger.info("=== 测试保存实时数据为今日行情 ===")
    from stock_data_manager import save_spot_as_daily_data
    saved_count = save_spot_as_daily_data(spot_data.head(10))  # 只测试前10条
    logger.info(f"✅ 保存今日行情成功，共 {saved_count} 条")
    return True


def test_fetch_and_save_history():
    """测试获取并保存历史数据"""
    logger.info("=== 测试获取并保存历史数据 ===")
    from data_processor import fetch_history
    from stock_data_manager import save_daily_data, get_missing_daily_data
    
    # 选择几个测试股票代码
    test_codes = ["000001", "000002", "600000"]
    logger.info(f"测试股票代码: {test_codes}")
    
    # 检查缺失数据
    missing_data = get_missing_daily_data(test_codes)
    logger.info(f"需要补充数据的股票: {len(missing_data)} 个")
    
    if missing_data:
        # 获取历史数据（只获取最近5天测试）
        history_data = fetch_history(list(missing_data.keys())[:2], days=5)  # 只测试前2个
        
        if history_data:
            # 保存到数据库
            saved_count = save_daily_data(history_data)
            logger.info(f"✅ 获取并保存历史数据成功，共 {saved_count} 条")
            return True, history_data
        else:
            logger.warning("⚠️ 历史数据获取为空")
            return False, None
    else:
        logger.info("✅ 所有测试股票数据都是最新的")
        return True, {}


def test_weekly_monthly_calculation():
    """测试周K月K计算"""
    logger.info("=== 测试周K月K计算 ===")
    from market_data_processor import calculate_and_save_weekly_data, calculate_and_save_monthly_data
    
    test_codes = ["000001", "000002"]
    
    # 计算周K
    weekly_count = calculate_and_save_weekly_data(test_codes)
    logger.info(f"✅ 计算周K线成功，共 {weekly_count} 条")
    
    # 计算月K
    monthly_count = calculate_and_save_monthly_data(test_codes)
    logger.info(f"✅ 计算月K线成功，共 {monthly_count} 条")
    
    return True


def test_data_loading():
    """测试从数据库加载数据"""
    logger.info("=== 测试从数据库加载数据 ===")
    from stock_data_manager import load_daily_data_for_analysis
    from market_data_processor import get_weekly_data, get_monthly_data
    
    test_codes = ["000001", "000002"]
    
    # 加载日K数据
    daily_data = load_daily_data_for_analysis(test_codes, limit=10)
    logger.info(f"✅ 加载日K数据成功，共 {len(daily_data)} 个股票")
    
    # 加载周K数据
    weekly_data = get_weekly_data(test_codes, limit=5)
    logger.info(f"✅ 加载周K数据成功，共 {len(weekly_data)} 条记录")
    
    # 加载月K数据
    monthly_data = get_monthly_data(test_codes, limit=3)
    logger.info(f"✅ 加载月K数据成功，共 {len(monthly_data)} 条记录")
    
    return True, daily_data


def test_factor_calculation(spot_data, daily_data):
    """测试因子计算"""
    logger.info("=== 测试因子计算 ===")
    from data_processor import compute_factors
    
    # 准备测试数据
    top_spot = spot_data.head(5).copy()  # 只测试前5个股票
    
    # 计算因子
    factors_df = compute_factors(top_spot, daily_data)
    
    if not factors_df.empty:
        logger.info(f"✅ 因子计算成功，共 {len(factors_df)} 条结果")
        logger.info(f"因子列: {list(factors_df.columns)}")
        
        # 显示前几条结果
        if len(factors_df) > 0:
            logger.info("前3条因子结果:")
            for _, row in factors_df.head(3).iterrows():
                logger.info(f"  {row.get('代码', 'N/A')} {row.get('名称', 'N/A')}: "
                          f"动量={row.get('动量因子', 'N/A'):.4f}, "
                          f"支撑={row.get('支撑因子', 'N/A'):.4f}")
        return True
    else:
        logger.warning("⚠️ 因子计算结果为空")
        return False


def test_technical_indicators():
    """测试技术指标计算"""
    logger.info("=== 测试技术指标计算 ===")
    from market_data_processor import calculate_technical_indicators
    from stock_data_manager import load_daily_data_for_analysis
    
    test_codes = ["000001", "000002"]
    daily_data = load_daily_data_for_analysis(test_codes, limit=100)  # 加载更多数据用于计算指标
    
    if not daily_data:
        logger.warning("⚠️ 没有可用的日线数据")
        return False
        
    # 对每只股票的数据分别计算技术指标
    success_count = 0
    for code, df in daily_data.items():
        # 计算技术指标
        indicators_df = calculate_technical_indicators(df)
        
        if not indicators_df.empty:
            logger.info(f"✅ {code} 技术指标计算成功，共 {len(indicators_df)} 条记录")
            logger.info(f"{code} 可用指标: {[col for col in indicators_df.columns if col not in df.columns]}")
            success_count += 1
    
    if success_count > 0:
        logger.info(f"✅ 共 {success_count} 只股票的技术指标计算成功")
        return True
    else:
        logger.warning("⚠️ 技术指标计算结果为空")
        return False


def check_database_content():
    """检查数据库内容"""
    logger.info("=== 检查数据库内容 ===")
    from sqlalchemy import create_engine, inspect
    from models import SQLALCHEMY_DATABASE_URL
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    inspector = inspect(engine)
    
    # 获取所有表
    tables = inspector.get_table_names()
    logger.info(f"数据库表: {tables}")
    
    # 显示每个表的前5条记录
    for table in tables:
        with engine.connect() as conn:
            result = conn.execute(f"SELECT * FROM {table} LIMIT 5").fetchall()
            logger.info(f"\n表 {table} 的前 {len(result)} 条记录:")
            for row in result:
                logger.info(f"  {row}")
    
    return True


def main():
    """主测试函数"""
    logger.info("\n" + "="*50)
    logger.info("📊 开始测试股票数据处理流程")
    logger.info("="*50 + "\n")
    
    success = True
    
    # 1. 初始化数据库
    if not test_database_setup():
        success = False
        logger.error("❌ 数据库初始化测试失败，终止测试")
        return False
    
    # 2. 获取实时行情
    spot_success, spot_data = test_fetch_spot_data()
    if not spot_success or spot_data is None:
        success = False
        logger.error("❌ 获取实时行情测试失败，终止测试")
        return False
    
    # 3. 保存股票基本信息
    if not test_save_basic_info(spot_data):
        success = False
        logger.warning("⚠️ 保存股票基本信息测试失败，继续执行其他测试...")
    
    # 4. 保存实时数据为今日行情
    if not test_save_spot_as_daily(spot_data):
        success = False
        logger.warning("⚠️ 保存今日行情测试失败，继续执行其他测试...")
    
    # 5. 获取并保存历史数据
    history_success, history_data = test_fetch_and_save_history()
    if not history_success:
        success = False
        logger.warning("⚠️ 获取并保存历史数据测试失败，继续执行其他测试...")
    
    # 6. 计算周K月K
    if not test_weekly_monthly_calculation():
        success = False
        logger.warning("⚠️ 周K月K计算测试失败，继续执行其他测试...")
    
    # 7. 测试数据加载
    data_loading_success, daily_data = test_data_loading()
    if not data_loading_success or daily_data is None:
        success = False
        logger.warning("⚠️ 数据加载测试失败，继续执行其他测试...")
    
    # 8. 测试因子计算
    if not test_factor_calculation(spot_data, daily_data if 'daily_data' in locals() else {}):
        success = False
        logger.warning("⚠️ 因子计算测试失败，继续执行其他测试...")
    
    # 9. 测试技术指标计算
    if not test_technical_indicators():
        success = False
        logger.warning("⚠️ 技术指标计算测试失败，继续执行其他测试...")
    
    # 10. 检查数据库内容
    if not check_database_content():
        success = False
        logger.warning("⚠️ 数据库内容检查失败，继续执行其他测试...")
    
    if success:
        logger.info("\n✅ 所有测试执行完成，没有发现错误！")
    else:
        logger.warning("\n⚠️ 测试完成，但部分测试未通过，请查看上面的日志了解详情。")
    
    return success



if __name__ == "__main__":
    df=ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20250101", end_date="20250906")
    print(df)
