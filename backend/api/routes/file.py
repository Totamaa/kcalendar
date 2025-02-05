import os
from datetime import datetime, timedelta
import hashlib
import time

from fastapi import APIRouter, HTTPException, Response, status, Request
from fastapi.responses import FileResponse

from config.logs import LoggerManager
from config.settings import get_settings

router = APIRouter()
logging = LoggerManager()
settings = get_settings()

@router.get(
    "/calendar.ics",
    response_class=FileResponse,
    status_code=200
)
async def get_calendar(request: Request):
    logging.info("Requesting calendar receive")
    try:
        file_path = "static/calendar.ics"
        date_format = "%a, %d %b %Y %H:%M:%S GMT"
        
        # Check if the file exists and get its last modified date
        file_stat = os.stat(file_path)
        last_modified = datetime.fromtimestamp(file_stat.st_mtime)
        last_modified_str = last_modified.strftime(date_format)
        
        # Generate an ETag which is a unique identifier hash for the file
        etag = hashlib.md5(f"{file_stat.st_mtime}:{file_stat.st_size}".encode()).hexdigest()
        
        if_none_match = request.headers.get("if-none-match")
        if_modified_since = request.headers.get("if-modified-since")
        
        # If the ETag or the last modified date match the request, return a 304 Not Modified response
        if (if_none_match and if_none_match == etag) or \
           (if_modified_since and datetime.strptime(if_modified_since, date_format) >= last_modified):
            return Response(status_code=status.HTTP_304_NOT_MODIFIED)
        
        response = FileResponse(
            path=file_path,
            media_type="text/calendar",
            filename="calendar.ics"
        )
        
        # Set the cache headers
        cache_duration = timedelta(minutes=settings.BACK_CACHE_DURATION)
        response.headers["Cache-Control"] = f"public, max-age={int(cache_duration.total_seconds())}"
        response.headers["Expires"] = (datetime.now() + cache_duration).strftime(date_format)
        
        response.headers["ETag"] = etag
        response.headers["Last-Modified"] = last_modified_str
        
        return response
        
    except Exception as e:
        logging.error(f"Error with the calendar: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error with the calendar")