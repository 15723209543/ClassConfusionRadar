"""
本文件的作用是：组织第一版课堂、文件、分段、分析和建议接口。
"""
from fastapi import APIRouter

from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.files import router as files_router
from app.api.v1.routes.knowledge_points import router as knowledge_points_router
from app.api.v1.routes.segments import router as segments_router
from app.api.v1.routes.sessions import router as sessions_router
from app.api.v1.routes.suggestions import router as suggestions_router
from app.core.config import get_settings

api_router = APIRouter(prefix=get_settings().api_v1_prefix)
api_router.include_router(sessions_router, tags=["sessions"])
api_router.include_router(knowledge_points_router, tags=["knowledge-points"])
api_router.include_router(segments_router, tags=["segments"])
api_router.include_router(files_router, tags=["files"])
api_router.include_router(analytics_router, tags=["analytics"])
api_router.include_router(suggestions_router, tags=["suggestions"])
