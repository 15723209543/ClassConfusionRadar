"""
本文件的作用是：实现测试数据集相关的核心业务处理。
"""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import bad_request
from app.models.enums import FileKind
from app.models.session import KnowledgePoint
from app.parsers.tabular import read_tabular_rows, validate_required_columns
from app.services import file_service
from app.services.session_service import get_session_or_404


FILE_ALIASES: dict[FileKind, tuple[str, ...]] = {
    FileKind.quiz: ("quiz", "课堂测验", "测验"),
    FileKind.submission: ("submission", "编程提交", "提交"),
    FileKind.interaction: ("interaction", "课堂互动", "互动"),
    FileKind.transcript: ("transcript", "课堂讲稿", "讲稿"),
    FileKind.ppt_timeline: ("ppt_timeline", "ppt-time", "ppt时间轴", "ppt_时间轴"),
}
SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xlsm"}


def import_dataset_zip(db: Session, session_id: int, filename: str, content: bytes) -> dict:
    get_session_or_404(db, session_id)
    if not filename.lower().endswith(".zip"):
        raise bad_request("课堂数据包必须是 ZIP 文件。")

    max_bytes = get_settings().max_dataset_zip_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise bad_request(f"ZIP 文件不能超过 {get_settings().max_dataset_zip_mb} MB。")

    try:
        archive = ZipFile(BytesIO(content))
    except BadZipFile as exc:
        raise bad_request("ZIP 文件无法读取，请重新压缩后再试。") from exc

    with archive:
        zip_files, ignored_files = _collect_zip_files(archive)
        if not zip_files:
            raise bad_request("ZIP 中没有识别到 quiz、submission、interaction、transcript 或 ppt_timeline 数据文件。")

        _validate_import_files(zip_files)
        manifest = _read_dataset_manifest(archive)
        new_point_ids = _sync_manifest_knowledge_points(db, session_id, manifest)

        imported_files = []
        try:
            for file_kind, item in zip_files.items():
                imported_files.append(
                    file_service.upload_data_file(
                        db,
                        session_id,
                        file_kind,
                        item["name"],
                        item["content"],
                    )
                )
        except Exception:
            for uploaded_file in reversed(imported_files):
                try:
                    file_service.delete_uploaded_file(db, uploaded_file.id)
                except Exception:
                    db.rollback()
            _rollback_knowledge_points(db, new_point_ids)
            raise

    return {
        "uploaded_files": imported_files,
        "knowledge_points_created": len(new_point_ids),
        "skipped_files": ignored_files,
        "manifest_found": manifest is not None,
    }


def _collect_zip_files(archive: ZipFile) -> tuple[dict[FileKind, dict], list[str]]:
    files_by_kind: dict[FileKind, dict] = {}
    ignored_names: list[str] = []
    unpacked_bytes = 0
    unpacked_limit = get_settings().max_dataset_zip_mb * 2 * 1024 * 1024

    for info in archive.infolist():
        if info.is_dir():
            continue
        # 导入前累计解压体积，避免压缩包展开后占用异常空间。
        unpacked_bytes += info.file_size
        if unpacked_bytes > unpacked_limit:
            raise bad_request("ZIP 解压后的数据量过大，请检查是否包含了无关文件。")

        path = PurePosixPath(info.filename)
        basename = path.name
        if not basename or basename.startswith(".") or basename.lower() == "manifest.json":
            continue

        kind = _guess_file_kind(basename)
        if kind is None:
            ignored_names.append(info.filename)
            continue
        if kind in files_by_kind:
            raise bad_request(f"ZIP 中出现了多份 {kind.value} 数据，请每类只保留一份。")

        suffix = PurePosixPath(basename).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            ignored_names.append(info.filename)
            continue

        files_by_kind[kind] = {"name": basename, "content": archive.read(info)}

    return files_by_kind, ignored_names


def _guess_file_kind(filename: str) -> FileKind | None:
    stem = PurePosixPath(filename).stem.lower().replace(" ", "_")
    for kind, aliases in FILE_ALIASES.items():
        if any(alias.lower() in stem for alias in aliases):
            return kind
    return None


def _validate_import_files(zip_files: dict[FileKind, dict]) -> None:
    # 所有文件先统一完成表头和行数据校验，避免导入一半后才发现格式错误。
    for file_kind, item in zip_files.items():
        rows = read_tabular_rows(item["name"], item["content"])
        validate_required_columns(file_kind, rows)
        file_service.validate_rows_for_import(file_kind, rows)


def _read_dataset_manifest(archive: ZipFile) -> dict | None:
    manifest_entries = [info for info in archive.infolist() if PurePosixPath(info.filename).name.lower() == "manifest.json"]
    if not manifest_entries:
        return None
    try:
        manifest_data = json.loads(archive.read(manifest_entries[0]).decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise bad_request("manifest.json 不是有效的 UTF-8 JSON。") from exc
    if not isinstance(manifest_data, dict):
        raise bad_request("manifest.json 顶层必须是 JSON 对象。")
    return manifest_data


def _sync_manifest_knowledge_points(db: Session, session_id: int, manifest: dict | None) -> list[int]:
    if not manifest:
        return []
    point_items = manifest.get("knowledge_points")
    if point_items is None:
        return []
    if not isinstance(point_items, list):
        raise bad_request("manifest.json 的 knowledge_points 必须是数组。")

    existing_point_names = set(
        db.scalars(select(KnowledgePoint.name).where(KnowledgePoint.session_id == session_id)).all()
    )
    new_point_ids: list[int] = []
    for index, point_item in enumerate(point_items, start=1):
        if isinstance(point_item, str):
            name = point_item.strip()
            topic_area = None
            description = None
        elif isinstance(point_item, dict):
            name = str(point_item.get("name") or "").strip()
            topic_area = str(point_item.get("topic_area") or "").strip() or None
            description = str(point_item.get("description") or "").strip() or None
        else:
            raise bad_request(f"manifest.json 第 {index} 个知识点格式不正确。")

        if not name or name in existing_point_names:
            continue
        knowledge_point = KnowledgePoint(
            session_id=session_id,
            name=name,
            topic_area=topic_area,
            description=description,
            display_order=len(existing_point_names) + 1,
        )
        db.add(knowledge_point)
        db.flush()
        new_point_ids.append(knowledge_point.id)
        existing_point_names.add(name)

    db.commit()
    return new_point_ids


def _rollback_knowledge_points(db: Session, ids: list[int]) -> None:
    if not ids:
        return
    for point_id in ids:
        knowledge_point = db.get(KnowledgePoint, point_id)
        if knowledge_point:
            db.delete(knowledge_point)
    db.commit()
