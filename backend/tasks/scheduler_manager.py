from apscheduler.schedulers.background import BackgroundScheduler

from services import EsportCalendarService
from config.settings import get_settings

# initialize the scheduler
scheduler = BackgroundScheduler()
settings = get_settings()

def start_scheduler():
    """Start the background scheduler to periodically update the esports calendar."""
    esport_calendar_service = EsportCalendarService()
    
    # schedule the update_calendar method to run at a fixed interval
    scheduler.add_job(
        esport_calendar_service.update_calendar, 
        "interval", 
        minutes=settings.BACK_PANDA_REFRESH_INTERVAL
    )
    scheduler.start() # start the scheduler

def stop_scheduler():
    """Shutdown the scheduler safely when the application stops."""
    scheduler.shutdown()