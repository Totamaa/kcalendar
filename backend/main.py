import time

from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager

from config.settings import get_settings
from config.logs import LoggerManager
from api.router import api_router
from tasks.scheduler_manager import start_scheduler, stop_scheduler
from services.esport_calendar import EsportCalendarService

def create_app() -> FastAPI:
    
    settings = get_settings()
    logging = LoggerManager()
    
    docs_url = None
    redoc_url = None
    if settings.ENVIRONMENT != "prod":
        docs_url = "/api"
        redoc_url = "/api/redoc"
        
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.info("Start backend")
        EsportCalendarService().update_calendar()
        start_scheduler()
        yield
        stop_scheduler()
        logging.info("Stop backend")
    
    app = FastAPI(
        title=settings.BACK_NAME,
        description=settings.BACK_DESCRIPTION,
        version=settings.BACK_VERSION,
        docs_url=docs_url,
        redoc_url=redoc_url,
        lifespan=lifespan,
    )
    
    @app.middleware("http")
    async def _add_process_time_header(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    app.include_router(api_router, prefix="/api")
    
    return app

app = create_app()