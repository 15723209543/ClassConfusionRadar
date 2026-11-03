"""
本文件的作用是：提供课堂文件相关的 HTTP 接口。
"""
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.enums import FileKind
from app.schemas.common import ApiMessage
from app.schemas.file import DatasetImportRead, UploadedFileRead
from app.services import dataset_service, file_service

router = APIRouter()


@router.get("/sessions/{session_id}/files", response_model=list[UploadedFileRead])
def list_files(session_id: int, db: Session = Depends(get_db_session)) -> list[UploadedFileRead]:
    return file_service.list_uploaded_files(db, session_id)


@router.post("/sessions/{session_id}/files", response_model=UploadedFileRead, status_code=status.HTTP_201_CREATED)
async def upload_file(
    session_id: int,
    file_kind: FileKind = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
) -> UploadedFileRead:
    content = await file.read()
    return file_service.upload_data_file(db, session_id, file_kind, file.filename or "", content)


@router.post(
    "/sessions/{session_id}/dataset-zip",
    response_model=DatasetImportRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_dataset_zip(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
) -> DatasetImportRead:
    content = await file.read()
    return dataset_service.import_dataset_zip(db, session_id, file.filename or "", content)


@router.delete("/files/{file_id}", response_model=ApiMessage)
def delete_file(file_id: int, db: Session = Depends(get_db_session)) -> ApiMessage:
    file_service.delete_uploaded_file(db, file_id)
    return ApiMessage(message="上传文件已删除。")
