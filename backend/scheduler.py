from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from api import run_analysis, run_extended_analysis
from models import RunRequest
import time
import pytz
import logging

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()


def daily_scheduled_analysis():
    """Scheduled task to run analysis and extended analysis daily at 00:00 Beijing time"""
    try:
        logger.info("Starting scheduled daily analysis...")
        
        # Run regular analysis with default parameters
        run_request = RunRequest(top_n=50, selected_factors=[], collect_latest_data=True)
        run_analysis(run_request)
        
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