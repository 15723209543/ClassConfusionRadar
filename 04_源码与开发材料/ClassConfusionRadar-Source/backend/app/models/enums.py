"""
本文件的作用是：定义enums相关的数据库模型或枚举。
"""
from enum import Enum


class SessionStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    analyzed = "analyzed"


class FileKind(str, Enum):
    quiz = "quiz"
    submission = "submission"
    interaction = "interaction"
    transcript = "transcript"
    ppt_timeline = "ppt_timeline"


class ParseStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    success = "success"
    failed = "failed"


class AttendanceStatus(str, Enum):
    present = "present"
    absent = "absent"
    late = "late"


class AnalysisStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class SuggestionStatus(str, Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"


class EnhancedAnalysisStatus(str, Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"
