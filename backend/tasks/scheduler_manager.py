from apscheduler.schedulers.background import BackgroundScheduler

from services import EsportCalendarService
from config.settings import get_settings

scheduler = BackgroundScheduler()
settings = get_settings()

def start_scheduler():
    esport_calendar_service = EsportCalendarService()
    scheduler.add_job(esport_calendar_service.update_calendar, "interval", minutes=settings.BACK_PANDA_REFRESH_INTERVAL)
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()