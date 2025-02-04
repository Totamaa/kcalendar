from fastapi import APIRouter
from .routes import file

api_router = APIRouter()

api_router.include_router(file.router, prefix="/files", tags=["File"])