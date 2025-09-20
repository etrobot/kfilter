from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from api import run_analysis, run_extended_analysis
from models import RunRequest, StockBasicInfo, DailyMarketData, WeeklyMarketData, MonthlyMarketData, get_session
from sqlmodel import or_
import time
import pytz
import logging

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()


def clean_st_and_delisted_stocks():
    """清理ST股票和退市股票的数据"""
    logger.info("Starting to clean ST and delisted stocks data...")
    
    with get_session() as session:
        try:
            # 查找符合条件的股票代码
            st_stocks = session.query(StockBasicInfo).filter(
                or_(
                    StockBasicInfo.name.like('*ST%'),
                    StockBasicInfo.name.like('退市%'),
                    StockBasicInfo.name.like('%退')
                )
            ).all()
            
            if not st_stocks:
                logger.info("No ST or delisted stocks found to clean.")
                return
                
            stock_codes = [stock.code for stock in st_stocks]
            logger.info(f"Found {len(stock_codes)} ST or delisted stocks to clean: {', '.join(stock_codes[:5])}{'...' if len(stock_codes) > 5 else ''}")
            
            # 删除日线数据
            daily_deleted = session.query(DailyMarketData).filter(
                DailyMarketData.code.in_(stock_codes)
            ).delete(synchronize_session=False)
            
            # 删除周线数据
            weekly_deleted = session.query(WeeklyMarketData).filter(
                WeeklyMarketData.code.in_(stock_codes)
            ).delete(synchronize_session=False)
            
            # 删除月线数据
            monthly_deleted = session.query(MonthlyMarketData).filter(
                MonthlyMarketData.code.in_(stock_codes)
            ).delete(synchronize_session=False)
            
            # 删除股票基本信息
            stocks_deleted = session.query(StockBasicInfo).filter(
                StockBasicInfo.code.in_(stock_codes)
            ).delete(synchronize_session=False)
            
            session.commit()
            
            logger.info(f"Cleaned {stocks_deleted} ST/delisted stocks and "
                      f"{daily_deleted} daily, {weekly_deleted} weekly, "
                      f"{monthly_deleted} monthly records.")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning ST and delisted stocks: {e}")
            raise


def daily_scheduled_analysis():
    """Scheduled task to run analysis and extended analysis daily at 00:00 Beijing time"""
    try:
        logger.info("Starting scheduled daily analysis...")
        
        # Run regular analysis with default parameters
        run_request = RunRequest(top_n=50, selected_factors=[], collect_latest_data=True)
        run_analysis(run_request)
        
        # 清理ST和退市股票数据
        clean_st_and_delisted_stocks()
        # Wait a bit before starting extended analysis
        time.sleep(5)
        
        # Run extended analysis
        logger.info("Starting scheduled extended analysis...")
        run_extended_analysis()
        
        logger.info("Scheduled daily analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Scheduled analysis failed: {e}")


def start_daily_scheduler():
    """Start the daily scheduler for automated analysis"""
    try:
        # Add job to run daily at 00:00 Beijing time
        beijing_tz = pytz.timezone('Asia/Shanghai')
        scheduler.add_job(
            daily_scheduled_analysis,
            trigger=CronTrigger(hour=0, minute=0, timezone=beijing_tz),
            id='daily_analysis',
            name='Daily Stock Analysis at 00:00 Beijing Time',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Daily scheduler started. Will run at 00:00 Beijing time daily")
        
        # Log the next run time
        job = scheduler.get_job('daily_analysis')
        if job:
            logger.info(f"Next scheduled run: {job.next_run_time}")
            
    except Exception as e:
        logger.error(f"Failed to start daily scheduler: {e}")