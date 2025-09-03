#!/usr/bin/env python3
"""
测试脚本：验证股票数据处理完整流程
包括：数据库创建、数据获取、存储、K线计算、因子分析
"""

import logging
import sys
from datetime import date
import pandas as pd

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_setup():
    """测试数据库初始化"""
    logger.info("=== 测试数据库初始化 ===")
    try:
        from models import create_db_and_tables
        create_db_and_tables()
        logger.info("✅ 数据库初始化成功")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        return False


def test_fetch_spot_data():
    """测试获取实时行情数据"""
    logger.info("=== 测试获取实时行情数据 ===")
    try:
        from data_processor import fetch_spot
        spot_data = fetch_spot()
        
        if spot_data.empty:
            logger.warning("⚠️ 实时行情数据为空")
            return False, None
            
        logger.info(f"✅ 获取实时行情成功，共 {len(spot_data)} 条记录")
        logger.info(f"数据列: {list(spot_data.columns)}")
        return True, spot_data
    except Exception as e:
        logger.error(f"❌ 获取实时行情失败: {e}")
        return False, None


def test_save_basic_info(spot_data):
    """测试保存股票基本信息"""
    logger.info("=== 测试保存股票基本信息 ===")
    try:
        from stock_data_manager import save_stock_basic_info
        saved_count = save_stock_basic_info(spot_data.head(10))  # 只测试前10条
        logger.info(f"✅ 保存股票基本信息成功，共 {saved_count} 条")
        return True
    except Exception as e:
        logger.error(f"❌ 保存股票基本信息失败: {e}")
        return False


def test_save_spot_as_daily(spot_data):
    """测试保存实时数据为今日行情"""
    logger.info("=== 测试保存实时数据为今日行情 ===")
    try:
        from stock_data_manager import save_spot_as_daily_data
        saved_count = save_spot_as_daily_data(spot_data.head(10))  # 只测试前10条
        logger.info(f"✅ 保存今日行情成功，共 {saved_count} 条")
        return True
    except Exception as e:
        logger.error(f"❌ 保存今日行情失败: {e}")
        return False


def test_fetch_and_save_history():
    """测试获取并保存历史数据"""
    logger.info("=== 测试获取并保存历史数据 ===")
    try:
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
            
    except Exception as e:
        logger.error(f"❌ 获取并保存历史数据失败: {e}")
        return False, None


def test_weekly_monthly_calculation():
    """测试周K月K计算"""
    logger.info("=== 测试周K月K计算 ===")
    try:
        from market_data_processor import calculate_and_save_weekly_data, calculate_and_save_monthly_data
        
        test_codes = ["000001", "000002"]
        
        # 计算周K
        weekly_count = calculate_and_save_weekly_data(test_codes)
        logger.info(f"✅ 计算周K线成功，共 {weekly_count} 条")
        
        # 计算月K
        monthly_count = calculate_and_save_monthly_data(test_codes)
        logger.info(f"✅ 计算月K线成功，共 {monthly_count} 条")
        
        return True
    except Exception as e:
        logger.error(f"❌ 周K月K计算失败: {e}")
        return False


def test_data_loading():
    """测试从数据库加载数据"""
    logger.info("=== 测试从数据库加载数据 ===")
    try:
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
    except Exception as e:
        logger.error(f"❌ 数据加载失败: {e}")
        return False, None


def test_factor_calculation(spot_data, daily_data):
    """测试因子计算"""
    logger.info("=== 测试因子计算 ===")
    try:
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
            
    except Exception as e:
        logger.error(f"❌ 因子计算失败: {e}")
        return False


def test_technical_indicators():
    """测试技术指标计算"""
    logger.info("=== 测试技术指标计算 ===")
    try:
        from market_data_processor import calculate_technical_indicators
        from stock_data_manager import load_daily_data_for_analysis
        
        # 加载一个股票的数据
        daily_data = load_daily_data_for_analysis(["000001"], limit=30)
        
        if daily_data and "000001" in daily_data:
            df = daily_data["000001"]
            indicators_df = calculate_technical_indicators(df)
            
            logger.info(f"✅ 技术指标计算成功，数据行数: {len(indicators_df)}")
            logger.info(f"包含指标: {[col for col in indicators_df.columns if col.startswith(('MA', 'RSI', 'BB_'))]}")
            return True
        else:
            logger.warning("⚠️ 没有找到测试数据")
            return False
            
    except Exception as e:
        logger.error(f"❌ 技术指标计算失败: {e}")
        return False


def check_database_content():
    """检查数据库内容"""
    logger.info("=== 检查数据库内容 ===")
    try:
        from sqlmodel import Session, select, func
        from models import engine, StockBasicInfo, DailyMarketData, WeeklyMarketData, MonthlyMarketData
        
        with Session(engine) as session:
            # 统计各表记录数
            basic_count = session.exec(select(func.count(StockBasicInfo.code))).one()
            daily_count = session.exec(select(func.count(DailyMarketData.id))).one()
            weekly_count = session.exec(select(func.count(WeeklyMarketData.id))).one()
            monthly_count = session.exec(select(func.count(MonthlyMarketData.id))).one()
            
            logger.info(f"✅ 数据库统计:")
            logger.info(f"  股票基本信息: {basic_count} 条")
            logger.info(f"  日K线数据: {daily_count} 条")
            logger.info(f"  周K线数据: {weekly_count} 条")
            logger.info(f"  月K线数据: {monthly_count} 条")
            
            # 显示最新的几条记录
            latest_daily = session.exec(
                select(DailyMarketData).order_by(DailyMarketData.date.desc()).limit(3)
            ).all()
            
            if latest_daily:
                logger.info("最新日K线记录:")
                for record in latest_daily:
                    logger.info(f"  {record.code} {record.date}: 收盘={record.close_price}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 数据库检查失败: {e}")
        return False


def main():
    """主测试函数"""
    logger.info("🚀 开始股票数据处理完整流程测试")
    
    results = []
    
    # 1. 测试数据库初始化
    results.append(("数据库初始化", test_database_setup()))
    
    # 2. 测试获取实时数据
    success, spot_data = test_fetch_spot_data()
    results.append(("获取实时行情", success))
    
    if not success or spot_data is None:
        logger.error("❌ 无法获取实时数据，后续测试无法进行")
        return False
    
    # 3. 测试保存基本信息
    results.append(("保存股票基本信息", test_save_basic_info(spot_data)))
    
    # 4. 测试保存今日行情
    results.append(("保存今日行情", test_save_spot_as_daily(spot_data)))
    
    # 5. 测试历史数据处理
    success, history_data = test_fetch_and_save_history()
    results.append(("获取并保存历史数据", success))
    
    # 6. 测试周K月K计算
    results.append(("周K月K计算", test_weekly_monthly_calculation()))
    
    # 7. 测试数据加载
    success, daily_data = test_data_loading()
    results.append(("数据加载", success))
    
    # 8. 测试因子计算
    if success and daily_data:
        results.append(("因子计算", test_factor_calculation(spot_data, daily_data)))
    
    # 9. 测试技术指标
    results.append(("技术指标计算", test_technical_indicators()))
    
    # 10. 检查数据库内容
    results.append(("数据库内容检查", check_database_content()))
    
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
        logger.info("🎉 所有测试通过！股票数据处理流程正常工作")
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