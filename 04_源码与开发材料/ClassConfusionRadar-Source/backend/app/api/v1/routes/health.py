"""
本文件的作用是：提供服务健康检查相关的 HTTP 接口。
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
