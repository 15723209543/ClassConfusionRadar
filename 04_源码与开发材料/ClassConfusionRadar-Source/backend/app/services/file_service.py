"""
本文件的作用是：实现课堂文件相关的核心业务处理。
"""
import hashlib
import hmac
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import bad_request, not_found
from app.models.enums import FileKind, ParseStatus
from app.models.records import InteractionRecord, QuizRecord, SessionStudent, Student, SubmissionRecord
from app.models.session import UploadedFile
from app.parsers.tabular import (
    infer_file_kind_from_rows,
    normalize_bool,
    normalize_float,
    read_tabular_rows,
    validate_required_columns,
)
from app.services.session_service import get_session_or_404, sync_session_status
from app.utils.files import build_storage_path


def list_uploaded_files(db: Session, session_id: int) -> list[UploadedFile]:
    get_session_or_404(db, session_id)
    return db.scalars(
        select(UploadedFile).where(UploadedFile.session_id == session_id).order_by(UploadedFile.created_at.desc())
    ).all()


def upload_data_file(db: Session, session_id: int, file_kind: FileKind, filename: str, content: bytes) -> UploadedFile:
    if not filename:
        raise bad_request("请选择要上传的文件。")

    class_session = get_session_or_404(db, session_id)
    storage_path = build_storage_path(get_settings().storage_dir, session_id, filename)
    storage_path.write_bytes(content)

    uploaded_file = UploadedFile(
        session_id=session_id,
        file_kind=file_kind,
        original_name=filename,
        storage_path=str(storage_path),
        parse_status=ParseStatus.processing,
    )
    db.add(uploaded_file)
    db.commit()
    db.refresh(uploaded_file)

    try:
        rows = read_tabular_rows(filename, content)
        inferred_kind = infer_file_kind_from_rows(rows)
        if inferred_kind is not None and inferred_kind != file_kind:
            file_kind = inferred_kind
            uploaded_file.file_kind = inferred_kind

        validate_required_columns(file_kind, rows)
        validate_rows_for_import(file_kind, rows)
        row_count = import_rows(db, session_id, uploaded_file.id, file_kind, rows)
        uploaded_file = db.get(UploadedFile, uploaded_file.id)
        uploaded_file.parse_status = ParseStatus.success
        uploaded_file.row_count = row_count
        uploaded_file.error_message = None
        sync_session_status(db, class_session)
        db.commit()
        db.refresh(uploaded_file)
        return uploaded_file
    except Exception as exc:
        db.rollback()
        uploaded_file = db.get(UploadedFile, uploaded_file.id)
        if uploaded_file:
            uploaded_file.parse_status = ParseStatus.failed
            uploaded_file.error_message = str(exc)
            db.commit()
            db.refresh(uploaded_file)
        raise


def delete_uploaded_file(db: Session, file_id: int) -> None:
    uploaded_file = db.get(UploadedFile, file_id)
    if not uploaded_file:
        raise not_found("上传文件不存在。")

    class_session = get_session_or_404(db, uploaded_file.session_id)
    storage_path = Path(uploaded_file.storage_path)
    if storage_path.exists():
        storage_path.unlink()

    db.delete(uploaded_file)
    db.flush()
    cleanup_session_students(db, class_session.id)
    cleanup_orphan_students(db)
    sync_session_status(db, class_session)
    db.commit()


def import_rows(
    db: Session,
    session_id: int,
    source_file_id: int,
    file_kind: FileKind,
    rows: list[dict],
) -> int:
    if file_kind in {FileKind.transcript, FileKind.ppt_timeline}:
        validate_material_rows(file_kind, rows)
        return len(rows)

    imported_count = 0
    for row in rows:
        student_code, student_name = normalize_student_identity(
            str(row["student_code"]), row.get("student_name")
        )
        student = get_or_create_student(db, student_code, student_name)
        ensure_session_student(db, session_id, student.id)

        if file_kind == FileKind.quiz:
            record = QuizRecord(
                session_id=session_id,
                student_id=student.id,
                source_file_id=source_file_id,
                question_code=str(row["question_code"]),
                score=normalize_float(row["score"], "score"),
                is_correct=normalize_bool(row["is_correct"]),
                event_minute=normalize_float(row["event_minute"], "event_minute"),
            )
        elif file_kind == FileKind.submission:
            record = SubmissionRecord(
                session_id=session_id,
                student_id=student.id,
                source_file_id=source_file_id,
                task_name=str(row["task_name"]),
                language=str(row["language"]),
                result_status=str(row["result_status"]),
                error_type=str(row["error_type"]) if row.get("error_type") not in (None, "") else None,
                error_message=str(row["error_message"]) if row.get("error_message") not in (None, "") else None,
                event_minute=normalize_float(row["event_minute"], "event_minute"),
            )
        else:
            record = InteractionRecord(
                session_id=session_id,
                student_id=student.id,
                source_file_id=source_file_id,
                event_type=str(row["event_type"]),
                value=normalize_float(row.get("value", 1), "value"),
                event_minute=normalize_float(row["event_minute"], "event_minute"),
            )

        db.add(record)
        imported_count += 1

    db.commit()
    return imported_count


def validate_rows_for_import(file_kind: FileKind, rows: list[dict]) -> None:
    if file_kind in {FileKind.transcript, FileKind.ppt_timeline}:
        validate_material_rows(file_kind, rows)
        return

    for index, row in enumerate(rows, start=2):
        student_code = str(row.get("student_code") or "").strip()
        if not student_code:
            raise bad_request(f"第 {index} 行缺少 student_code。")

        normalize_float(row["event_minute"], f"event_minute (line {index})")
        if file_kind == FileKind.quiz:
            normalize_float(row["score"], f"score (line {index})")
            normalize_bool(row["is_correct"])
        elif file_kind == FileKind.interaction and row.get("value") not in (None, ""):
            normalize_float(row["value"], f"value (line {index})")


def normalize_student_identity(student_code: str, student_name: object | None) -> tuple[str, str]:
    code = student_code.strip()
    if not code:
        raise bad_request("student_code 不能为空。")

    settings = get_settings()
    if not settings.anonymize_students:
        name = str(student_name).strip() if student_name not in (None, "") else code
        return code, name

    digest = hmac.new(
        settings.privacy_salt.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:12]
    return f"anon_{digest}", f"学生-{digest[:6].upper()}"


def validate_material_rows(file_kind: FileKind, rows: list[dict]) -> None:
    for index, row in enumerate(rows, start=2):
        start_minute = normalize_float(row["start_minute"], f"start_minute (line {index})")
        end_minute = normalize_float(row["end_minute"], f"end_minute (line {index})")
        if end_minute <= start_minute:
            raise bad_request(f"{file_kind.value} 文件第 {index} 行的结束时间必须大于开始时间。")

        if file_kind == FileKind.transcript and not str(row.get("text") or "").strip():
            raise bad_request(f"transcript 文件第 {index} 行缺少 text。")

        if file_kind == FileKind.ppt_timeline:
            slide_index = row.get("slide_index")
            if slide_index in (None, ""):
                raise bad_request(f"ppt_timeline 文件第 {index} 行缺少 slide_index。")
            try:
                int(float(slide_index))
            except (TypeError, ValueError) as exc:
                raise bad_request(f"ppt_timeline 文件第 {index} 行的 slide_index 必须为整数。") from exc


def get_or_create_student(db: Session, student_code: str, student_name: str) -> Student:
    student = db.scalars(select(Student).where(Student.student_code == student_code)).first()
    if student:
        if student_name and student.display_name != student_name:
            student.display_name = student_name
        return student

    student = Student(student_code=student_code, display_name=student_name)
    db.add(student)
    db.flush()
    return student


def ensure_session_student(db: Session, session_id: int, student_id: int) -> None:
    mapping = db.scalars(
        select(SessionStudent).where(
            SessionStudent.session_id == session_id,
            SessionStudent.student_id == student_id,
        )
    ).first()
    if not mapping:
        db.add(SessionStudent(session_id=session_id, student_id=student_id))
        db.flush()


def cleanup_session_students(db: Session, session_id: int) -> None:
    active_student_ids = set(
        db.scalars(select(QuizRecord.student_id).where(QuizRecord.session_id == session_id)).all()
    )
    active_student_ids.update(
        db.scalars(select(SubmissionRecord.student_id).where(SubmissionRecord.session_id == session_id)).all()
    )
    active_student_ids.update(
        db.scalars(select(InteractionRecord.student_id).where(InteractionRecord.session_id == session_id)).all()
    )

    mappings = db.scalars(select(SessionStudent).where(SessionStudent.session_id == session_id)).all()
    for mapping in mappings:
        if mapping.student_id not in active_student_ids:
            db.delete(mapping)


def cleanup_orphan_students(db: Session) -> None:
    mapped_student_ids = set(db.scalars(select(SessionStudent.student_id)).all())
    students = db.scalars(select(Student)).all()
    for student in students:
        if student.id not in mapped_student_ids:
            db.delete(student)
