from fastapi import APIRouter

from .health import router as health_router
from .ask import router as ask_router
from .stocks import router as stocks_router
from .manage import router as manage_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(ask_router)
api_router.include_router(manage_router)  # /stocks/search, /stocks/manage 먼저 등록
api_router.include_router(stocks_router)
