"""
本文件的作用是：解析上传的表格数据并转换为系统内部记录。
"""
import csv
from io import BytesIO, StringIO
from typing import Any

from openpyxl import load_workbook

from app.core.errors import bad_request
from app.models.enums import FileKind


REQUIRED_COLUMNS: dict[FileKind, set[str]] = {
    FileKind.quiz: {"student_code", "question_code", "score", "is_correct", "event_minute"},
    FileKind.submission: {"student_code", "task_name", "language", "result_status", "event_minute"},
    FileKind.interaction: {"student_code", "event_type", "event_minute"},
    FileKind.transcript: {"start_minute", "end_minute", "text"},
    FileKind.ppt_timeline: {"slide_index", "start_minute", "end_minute"},
}


def read_tabular_rows(filename: str, content: bytes) -> list[dict[str, Any]]:
    suffix = filename.lower().split(".")[-1]
    if suffix == "csv":
        decoded = decode_csv_content(content)
        reader = csv.DictReader(StringIO(decoded))
        return [normalize_row(row) for row in reader if row]

    if suffix in {"xlsx", "xlsm"}:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(header).strip() if header is not None else "" for header in rows[0]]
        parsed_rows: list[dict[str, Any]] = []
        for raw_row in rows[1:]:
            row = {headers[index]: raw_row[index] for index in range(len(headers)) if headers[index]}
            if any(value not in (None, "") for value in row.values()):
                parsed_rows.append(normalize_row(row))
        return parsed_rows

    raise bad_request("仅支持上传 CSV 或 XLSX 文件。")


def decode_csv_content(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise bad_request("CSV 文件编码无法识别，请优先使用 UTF-8 或 GBK/GB18030 编码后重试。")




def infer_file_kind_from_rows(rows: list[dict[str, Any]]) -> FileKind | None:
    if not rows:
        return None

    headers = set(rows[0].keys())
    matches = [kind for kind, required in REQUIRED_COLUMNS.items() if required.issubset(headers)]
    if len(matches) == 1:
        return matches[0]
    return None

def validate_required_columns(file_kind: FileKind, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise bad_request("上传文件为空，或缺少可识别的数据行。")

    headers = set(rows[0].keys())
    missing = REQUIRED_COLUMNS[file_kind] - headers
    if missing:
        raise bad_request(f"文件缺少必填列：{', '.join(sorted(missing))}")


def normalize_bool(value: Any) -> bool:
    truthy = {"1", "true", "yes", "y", "是"}
    falsy = {"0", "false", "no", "n", "否"}

    if isinstance(value, bool):
        return value

    value_str = str(value).strip().lower()
    if value_str in truthy:
        return True
    if value_str in falsy:
        return False
    raise bad_request(f"无法识别布尔值：{value}")


def normalize_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise bad_request(f"字段 {field_name} 需要为数字。") from exc


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key).strip(): value.strip() if isinstance(value, str) else value
        for key, value in row.items()
        if key is not None
    }
