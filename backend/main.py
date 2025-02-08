import time

from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager

from config.settings import get_settings
from config.logs import LoggerManager
from api.router import api_router
from tasks.scheduler_manager import start_scheduler, stop_scheduler
from services.esport_calendar import EsportCalendarService

def create_app() -> FastAPI:
    """Initialize and configure the FastAPI application."""
    
    settings = get_settings()
    logging = LoggerManager()
    
    # Disable API docs in production
    docs_url = None
    redoc_url = None
    if settings.ENVIRONMENT != "prod":
        docs_url = "/api"
        redoc_url = "/api/redoc"
        
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application startup and shutdown events."""
        logging.info("Start backend")
        
        # Run an initial calendar update before starting the scheduler
        EsportCalendarService().update_calendar()
        
        # Start the background scheduler
        start_scheduler()
        
        yield # Keep the application running
        
        # Stop the scheduler on shutdown
        stop_scheduler()
        logging.info("Stop backend")
    
    # Create FastAPI app with settings
    app = FastAPI(
        title=settings.BACK_NAME,
        description=settings.BACK_DESCRIPTION,
        version=settings.BACK_VERSION,
        docs_url=docs_url,
        redoc_url=redoc_url,
        lifespan=lifespan, # Attach the startup/shutdown manager
    )
    
    @app.middleware("http")
    async def _add_process_time_header(request: Request, call_next):
        """Middleware to measure and add request processing time to response headers."""
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    return app

app = create_app() # Create the application instance