"""
本文件的作用是：汇总并注册后端各版本接口路由。
"""
from fastapi import APIRouter

from app.api.v1.api import api_router
from app.api.v1.routes.health import router as health_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(api_router)
