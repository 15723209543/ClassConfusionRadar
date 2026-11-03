"""
本文件的作用是：提供文件处理或界面文本转换等通用工具。
"""
import re
from datetime import datetime, timezone
from pathlib import Path


def safe_filename(filename: str) -> str:
    clean_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", filename)
    return clean_name or "upload.csv"


def build_storage_path(base_dir: str, session_id: int, filename: str) -> Path:
    session_dir = Path(base_dir) / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return session_dir / f"{timestamp}_{safe_filename(filename)}"
