"""
本文件的作用是：为后端测试创建隔离数据库、应用实例和接口客户端。
"""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:
    database_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session, tmp_path) -> Generator[TestClient, None, None]:
    from app.core.config import get_settings

    settings = get_settings()
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path / "uploads")

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    settings.storage_dir = original_storage_dir
