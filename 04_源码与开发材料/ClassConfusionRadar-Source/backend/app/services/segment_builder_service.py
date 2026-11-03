"""
本文件的作用是：根据 PPT 时间窗、课堂讲稿和知识点自动构建教学分段。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request
from app.models.enums import FileKind, ParseStatus
from app.models.session import KnowledgePoint, TeachingSegment, UploadedFile
from app.parsers.tabular import normalize_float, read_tabular_rows, validate_required_columns
from app.schemas.segment import AutoSegmentBuildResult, AutoSegmentSourceInfo, TeachingSegmentRead
from app.services.segment_service import validate_segment_payload
from app.services.session_service import get_session_or_404, sync_session_status


GENERIC_SLIDE_TITLES = {
    "目录",
    "contents",
    "agenda",
    "summary",
    "总结",
    "thanks",
    "thank you",
    "q&a",
    "qa",
    "封面",
    "首页",
    "标题",
}


@dataclass
class TranscriptChunk:
    start_minute: float
    end_minute: float
    speaker: str | None
    text: str


@dataclass
class SlideWindow:
    slide_index: int
    slide_title: str | None
    start_minute: float
    end_minute: float


def auto_build_segments(db: Session, session_id: int, replace_existing: bool = False) -> AutoSegmentBuildResult:
    class_session = get_session_or_404(db, session_id)
    transcript_file = find_latest_uploaded_file(db, session_id, FileKind.transcript)
    ppt_timeline_file = find_latest_uploaded_file(db, session_id, FileKind.ppt_timeline)

    missing_files: list[str] = []
    if not transcript_file:
        missing_files.append("transcript")
    if not ppt_timeline_file:
        missing_files.append("ppt_timeline")
    if missing_files:
        raise bad_request(
            f"自动分段需要先上传并成功解析这些文件：{', '.join(missing_files)}。"
        )

    if class_session.segments and not replace_existing:
        raise bad_request("当前课堂已存在教学分段。如需重新生成，请勾选替换现有分段。")

    transcript_rows = read_uploaded_rows(transcript_file)
    ppt_rows = read_uploaded_rows(ppt_timeline_file)
    transcript_chunks = parse_transcript_sections(transcript_rows, class_session.duration_minutes)
    slide_windows = parse_ppt_windows(ppt_rows, class_session.duration_minutes)
    knowledge_points = sorted(class_session.knowledge_points, key=lambda item: item.display_order)

    raw_suggested_segments = build_segment_suggestions(
        slide_windows=slide_windows,
        transcript_chunks=transcript_chunks,
        knowledge_points=knowledge_points,
    )
    suggested_segments = merge_neighboring_segments(raw_suggested_segments)
    if not suggested_segments:
        raise bad_request("未能根据 transcript 与 PPT 时间轴生成有效教学分段，请检查时间窗和讲稿内容。")

    if replace_existing and class_session.segments:
        for segment in list(class_session.segments):
            db.delete(segment)
        db.flush()

    created_segments: list[TeachingSegment] = []
    for index, suggestion in enumerate(suggested_segments, start=1):
        validate_segment_payload(
            db=db,
            session_id=session_id,
            start_minute=suggestion["start_minute"],
            end_minute=suggestion["end_minute"],
            current_segment_id=None,
            session_duration=class_session.duration_minutes,
        )

        segment = TeachingSegment(
            session_id=session_id,
            knowledge_point_id=suggestion["knowledge_point_id"],
            title=suggestion["title"],
            start_minute=suggestion["start_minute"],
            end_minute=suggestion["end_minute"],
            display_order=index,
            teacher_notes=suggestion["teacher_notes"],
        )
        db.add(segment)
        db.flush()
        created_segments.append(segment)

    sync_session_status(db, class_session)
    db.commit()
    for segment in created_segments:
        db.refresh(segment)

    return AutoSegmentBuildResult(
        created_count=len(created_segments),
        replaced_existing=replace_existing,
        transcript_chunk_count=len(transcript_chunks),
        slide_window_count=len(slide_windows),
        source_files=AutoSegmentSourceInfo(
            transcript_file_id=transcript_file.id,
            transcript_filename=transcript_file.original_name,
            ppt_timeline_file_id=ppt_timeline_file.id,
            ppt_timeline_filename=ppt_timeline_file.original_name,
        ),
        message=(
            f"已根据 transcript 与 PPT 时间轴生成 {len(created_segments)} 个教学分段"
            f"（原始候选 {len(raw_suggested_segments)} 个，已自动合并连续同知识点页面）。"
        ),
        segments=[TeachingSegmentRead.model_validate(segment, from_attributes=True) for segment in created_segments],
    )


def find_latest_uploaded_file(db: Session, session_id: int, file_kind: FileKind) -> UploadedFile | None:
    return db.scalars(
        select(UploadedFile)
        .where(
            UploadedFile.session_id == session_id,
            UploadedFile.file_kind == file_kind,
            UploadedFile.parse_status == ParseStatus.success,
        )
        .order_by(UploadedFile.id.desc())
    ).first()


def read_uploaded_rows(uploaded_file: UploadedFile) -> list[dict]:
    storage_path = Path(uploaded_file.storage_path)
    if not storage_path.exists():
        raise bad_request(f"上传文件 {uploaded_file.original_name} 不存在，请重新上传后再试。")

    content = storage_path.read_bytes()
    rows = read_tabular_rows(uploaded_file.original_name, content)
    validate_required_columns(uploaded_file.file_kind, rows)
    return rows


def parse_transcript_sections(rows: list[dict], session_duration: int) -> list[TranscriptChunk]:
    parsed_rows: list[TranscriptChunk] = []
    for index, row in enumerate(rows, start=2):
        start_minute = normalize_float(row["start_minute"], f"transcript.start_minute line {index}")
        end_minute = normalize_float(row["end_minute"], f"transcript.end_minute line {index}")
        if end_minute <= start_minute:
            raise bad_request(f"transcript 文件第 {index} 行的结束时间必须大于开始时间。")

        clipped_start = max(0.0, start_minute)
        clipped_end = min(float(session_duration), end_minute)
        if clipped_end <= clipped_start:
            continue

        text = str(row.get("text") or "").strip()
        if not text:
            continue

        speaker = str(row.get("speaker") or "").strip() or None
        parsed_rows.append(
            TranscriptChunk(
                start_minute=clipped_start,
                end_minute=clipped_end,
                speaker=speaker,
                text=text,
            )
        )

    if not parsed_rows:
        raise bad_request("transcript 文件中没有可用的讲稿片段。")
    return parsed_rows


def parse_ppt_windows(rows: list[dict], session_duration: int) -> list[SlideWindow]:
    raw_windows: list[SlideWindow] = []
    for index, row in enumerate(rows, start=2):
        start_minute = normalize_float(row["start_minute"], f"ppt_timeline.start_minute line {index}")
        end_minute = normalize_float(row["end_minute"], f"ppt_timeline.end_minute line {index}")
        if end_minute <= start_minute:
            raise bad_request(f"ppt_timeline 文件第 {index} 行的结束时间必须大于开始时间。")

        slide_index_raw = row.get("slide_index")
        if slide_index_raw in (None, ""):
            raise bad_request(f"ppt_timeline 文件第 {index} 行缺少 slide_index。")
        try:
            slide_index = int(float(slide_index_raw))
        except (TypeError, ValueError) as exc:
            raise bad_request(f"ppt_timeline 文件第 {index} 行的 slide_index 必须为整数。") from exc

        raw_windows.append(
            SlideWindow(
                slide_index=slide_index,
                slide_title=str(row.get("slide_title") or "").strip() or None,
                start_minute=start_minute,
                end_minute=end_minute,
            )
        )

    raw_windows.sort(key=lambda item: (item.start_minute, item.slide_index))
    normalized_windows: list[SlideWindow] = []
    last_end = 0.0
    for window in raw_windows:
        adjusted_start = max(last_end, window.start_minute, 0.0)
        adjusted_end = min(float(session_duration), window.end_minute)
        if adjusted_end <= adjusted_start:
            continue
        normalized_windows.append(
            SlideWindow(
                slide_index=window.slide_index,
                slide_title=window.slide_title,
                start_minute=adjusted_start,
                end_minute=adjusted_end,
            )
        )
        last_end = adjusted_end

    if not normalized_windows:
        raise bad_request("ppt_timeline 文件中没有可用的时间窗。")
    return normalized_windows


def build_segment_suggestions(
    slide_windows: list[SlideWindow],
    transcript_chunks: list[TranscriptChunk],
    knowledge_points: list[KnowledgePoint],
) -> list[dict]:
    suggestions: list[dict] = []
    # 以 PPT 时间窗为骨架，叠加对应讲稿内容和知识点匹配结果。
    for slide in slide_windows:
        overlapped_chunks = [
            chunk
            for chunk in transcript_chunks
            if chunk.end_minute > slide.start_minute and chunk.start_minute < slide.end_minute
        ]
        transcript_text = " ".join(chunk.text for chunk in overlapped_chunks).strip()
        knowledge_point = match_knowledge_point(slide.slide_title, transcript_text, knowledge_points)
        title = choose_segment_title(slide, transcript_text, knowledge_point)

        if not title:
            continue

        teacher_notes = compose_teacher_notes(
            slide=slide,
            transcript_text=transcript_text,
            transcript_count=len(overlapped_chunks),
            knowledge_point_name=knowledge_point.name if knowledge_point else None,
        )
        suggestions.append(
            {
                "knowledge_point_id": knowledge_point.id if knowledge_point else None,
                "title": title,
                "start_minute": round(slide.start_minute, 2),
                "end_minute": round(slide.end_minute, 2),
                "teacher_notes": teacher_notes,
            }
        )
    return suggestions



def merge_neighboring_segments(suggestions: list[dict]) -> list[dict]:
    """把时间连续、知识点相同的 PPT 候选段合在一起。"""
    # 只有时间连续且知识点一致的候选段才允许合并。
    merged: list[dict] = []
    for suggestion in suggestions:
        if not merged:
            merged.append(dict(suggestion))
            continue

        previous = merged[-1]
        same_knowledge_point = (
            previous.get("knowledge_point_id") is not None
            and previous.get("knowledge_point_id") == suggestion.get("knowledge_point_id")
        )
        near_continuous = abs(float(previous["end_minute"]) - float(suggestion["start_minute"])) <= 0.15
        if same_knowledge_point and near_continuous:
            previous["end_minute"] = suggestion["end_minute"]
            previous["teacher_notes"] = (
                f"{previous.get('teacher_notes') or ''} 自动合并连续同知识点页面：{suggestion.get('title')} "
                f"（{suggestion.get('start_minute')}-{suggestion.get('end_minute')} 分钟）。"
            ).strip()
            continue

        merged.append(dict(suggestion))
    return merged

def choose_segment_title(
    slide: SlideWindow,
    transcript_text: str,
    knowledge_point: KnowledgePoint | None,
) -> str:
    slide_title = normalize_text(slide.slide_title or "")
    if slide_title and not is_generic_ppt_title(slide_title):
        return slide_title

    if knowledge_point:
        return f"{knowledge_point.name}讲解"

    if transcript_text:
        return f"第 {slide.slide_index} 页：{shorten_text(transcript_text, 18)}"

    if slide_title:
        return f"第 {slide.slide_index} 页：{slide_title}"
    return f"第 {slide.slide_index} 页讲解"


def match_knowledge_point(
    slide_title: str | None,
    transcript_text: str,
    knowledge_points: list[KnowledgePoint],
) -> KnowledgePoint | None:
    if not knowledge_points:
        return None

    source_text = " ".join(part for part in [slide_title or "", transcript_text] if part).strip()
    if not source_text:
        return None

    best_match: KnowledgePoint | None = None
    best_score = 0
    for knowledge_point in knowledge_points:
        weighted_score = score_point_match(source_text, knowledge_point)
        if weighted_score > best_score:
            best_score = weighted_score
            best_match = knowledge_point

    return best_match if best_score >= 20 else None


def score_point_match(source_text: str, knowledge_point: KnowledgePoint) -> int:
    weighted_score = 0
    source_compact = compact_for_matching(source_text)
    source_terms = extract_match_terms(source_text)

    name_compact = compact_for_matching(knowledge_point.name)
    if name_compact and name_compact in source_compact:
        weighted_score += 100

    for term in extract_match_terms(knowledge_point.name):
        if term in source_terms:
            weighted_score += 15

    if knowledge_point.topic_area:
        topic_compact = compact_for_matching(knowledge_point.topic_area)
        if topic_compact and topic_compact in source_compact:
            weighted_score += 25
        for term in extract_match_terms(knowledge_point.topic_area):
            if term in source_terms:
                weighted_score += 8

    return weighted_score


def compose_teacher_notes(
    slide: SlideWindow,
    transcript_text: str,
    transcript_count: int,
    knowledge_point_name: str | None,
) -> str:
    parts = [
        f"自动生成：依据 PPT 第 {slide.slide_index} 页的时间窗（{round(slide.start_minute, 2)}-{round(slide.end_minute, 2)} 分钟）创建。",
        f"对齐 transcript 片段 {transcript_count} 条。",
    ]
    if slide.slide_title:
        parts.append(f"PPT 标题：{slide.slide_title}。")
    if knowledge_point_name:
        parts.append(f"推测关联知识点：{knowledge_point_name}。")
    if transcript_text:
        parts.append(f"讲解摘要：{shorten_text(transcript_text, 48)}。")
    else:
        parts.append("该页未匹配到 transcript 文本，请教师手动复核。")
    return " ".join(parts)


def is_generic_ppt_title(title: str) -> bool:
    compact = compact_for_matching(title)
    return compact in {compact_for_matching(item) for item in GENERIC_SLIDE_TITLES}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def compact_for_matching(value: str) -> str:
    return re.sub(r"\s+", "", value.lower())


def extract_match_terms(value: str) -> set[str]:
    normalized = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", value.lower())
    return {item for item in normalized.split() if len(item) >= 2}


def shorten_text(value: str, max_length: int) -> str:
    cleaned = normalize_text(value)
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[:max_length].rstrip()}..."
