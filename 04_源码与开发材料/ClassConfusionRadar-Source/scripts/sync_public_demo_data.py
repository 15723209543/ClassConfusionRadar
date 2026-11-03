"""
本文件的作用是：将公开演示数据同步到源码与参赛材料约定的目录中。
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import ssl
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib import parse, request


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "docs" / "samples" / "public-demo"
CS50_WEEK_URL = "https://cs50.harvard.edu/python/weeks/2/"
CS50_TRANSCRIPT_URL = "https://cdn.cs50.net/python/2022/x/lectures/2/lang/en/lecture2.txt"
CS50_NOTES_URL = "https://cs50.harvard.edu/python/notes/2/"
AIZU_RECENT_URL = "https://judgeapi.u-aizu.ac.jp/submission_records/recent"

TARGET_PROBLEM_IDS = {
    "ITP1_2_A",
    "ITP1_2_B",
    "ITP1_2_C",
    "ITP1_3_A",
    "ITP1_3_B",
}
STATUS_LABELS = {
    0: ("compile_error", "Compile Error"),
    1: ("wrong_answer", "Wrong Answer"),
    2: ("runtime_error", "Time Limit Exceeded"),
    3: ("runtime_error", "Memory Limit Exceeded"),
    4: ("success", None),
    5: ("runtime_error", "Judge Not Available"),
    6: ("runtime_error", "Output Limit Exceeded"),
    7: ("runtime_error", "Runtime Error"),
    8: ("wrong_answer", "Presentation Error"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a public-source demo sample pack.")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="Directory to write the public demo sample pack.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    week_html = fetch_text(CS50_WEEK_URL)
    notes_html = fetch_text(CS50_NOTES_URL)
    transcript_text = fetch_text(CS50_TRANSCRIPT_URL)
    recent_submissions = fetch_json(AIZU_RECENT_URL, verify_ssl=False)

    transcript_rows = build_transcript_rows(transcript_text)
    slide_rows = build_slide_rows(notes_html, transcript_rows)
    submission_rows = build_submission_rows(recent_submissions, slide_rows)

    write_csv(output_dir / "transcript_demo.csv", transcript_rows)
    write_csv(output_dir / "ppt_timeline_demo.csv", slide_rows)
    write_csv(output_dir / "submission_demo.csv", submission_rows)
    write_sources_markdown(
        output_dir / "SOURCES.md",
        transcript_rows=transcript_rows,
        slide_rows=slide_rows,
        submission_rows=submission_rows,
        week_html=week_html,
    )

    print(f"Public demo sample pack generated at: {output_dir}")
    print(f"Transcript rows: {len(transcript_rows)}")
    print(f"Slide windows: {len(slide_rows)}")
    print(f"Submission rows: {len(submission_rows)}")
    return 0


def fetch_text(url: str, verify_ssl: bool = True) -> str:
    context = None if verify_ssl else ssl._create_unverified_context()
    req = request.Request(url, headers={"User-Agent": "ClassConfusionRadar/1.0"})
    with request.urlopen(req, timeout=30, context=context) as response:
        return response.read().decode("utf-8", errors="ignore")


def fetch_json(url: str, verify_ssl: bool = True) -> list[dict]:
    return json.loads(fetch_text(url, verify_ssl=verify_ssl))


def build_transcript_rows(transcript_text: str) -> list[dict[str, object]]:
    paragraphs = [
        normalize_whitespace(paragraph)
        for paragraph in transcript_text.split("\n\n")
        if normalize_whitespace(paragraph)
    ]

    rows: list[dict[str, object]] = []
    current_minute = 0.0
    for paragraph in paragraphs[:18]:
        words = len(paragraph.split())
        duration_minutes = max(0.8, round(words / 150, 2))
        next_minute = round(current_minute + duration_minutes, 2)
        rows.append(
            {
                "start_minute": round(current_minute, 2),
                "end_minute": next_minute,
                "speaker": "David Malan",
                "text": paragraph,
            }
        )
        current_minute = next_minute
    return rows


def build_slide_rows(notes_html: str, transcript_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    headings = extract_h2_headings(notes_html)
    if not headings:
        raise RuntimeError("No section headings were found in the CS50 notes page.")

    bucket_size = max(1, math.ceil(len(transcript_rows) / len(headings)))
    slide_rows: list[dict[str, object]] = []

    for index, heading in enumerate(headings, start=1):
        start_row = transcript_rows[min((index - 1) * bucket_size, len(transcript_rows) - 1)]
        end_row = transcript_rows[min(index * bucket_size - 1, len(transcript_rows) - 1)]
        slide_rows.append(
            {
                "slide_index": index,
                "start_minute": start_row["start_minute"],
                "end_minute": end_row["end_minute"],
                "slide_title": heading,
            }
        )

    return slide_rows


def build_submission_rows(recent_submissions: list[dict], slide_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    filtered = [
        item
        for item in recent_submissions
        if item.get("language") == "Python3" and item.get("problemId") in TARGET_PROBLEM_IDS
    ]
    if not filtered:
        raise RuntimeError("No suitable AIZU Python submissions were found in the recent submission feed.")

    # Keep the most recent 10 rows to keep the demo compact and reproducible enough.
    filtered = filtered[:10]
    practice_start = float(slide_rows[max(0, len(slide_rows) - 3)]["start_minute"])
    practice_end = float(slide_rows[-1]["end_minute"])
    if practice_end <= practice_start:
        practice_end = practice_start + 8

    time_step = max(0.7, round((practice_end - practice_start) / max(1, len(filtered)), 2))

    rows: list[dict[str, object]] = []
    for index, item in enumerate(reversed(filtered), start=1):
        result_status, error_type = STATUS_LABELS.get(int(item.get("status", -1)), ("runtime_error", "Unknown Status"))
        event_minute = round(practice_start + (index - 1) * time_step, 2)
        original_user = str(item.get("userId") or f"user_{index}")
        anonymized_code = f"AIZU_{index:02d}"
        rows.append(
            {
                "student_code": anonymized_code,
                "student_name": anonymized_code,
                "task_name": f"{item.get('problemId')} {item.get('problemTitle')}",
                "language": "python",
                "result_status": result_status,
                "error_type": error_type or "",
                "error_message": build_error_message(item, error_type),
                "event_minute": event_minute,
                "source_user_id": original_user,
                "source_judge_id": item.get("judgeId"),
            }
        )

    return rows


def build_error_message(item: dict, error_type: str | None) -> str:
    if not error_type:
        return ""

    cpu_time = item.get("cpuTime")
    memory = item.get("memory")
    accuracy = item.get("accuracy")
    parts = [str(error_type)]
    if accuracy:
        parts.append(f"accuracy={accuracy}")
    if cpu_time not in (None, ""):
        parts.append(f"cpu={cpu_time}ms")
    if memory not in (None, ""):
        parts.append(f"memory={memory}KB")
    return "; ".join(parts)


def extract_h2_headings(html_text: str) -> list[str]:
    matches = re.findall(r"<h2[^>]*>(.*?)</h2>", html_text, flags=re.IGNORECASE | re.DOTALL)
    headings = []
    for match in matches:
        cleaned = normalize_whitespace(strip_tags(html.unescape(match)))
        if cleaned:
            headings.append(cleaned)
    return headings


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    if not rows:
        raise RuntimeError(f"No rows available for {path.name}")

    fieldnames = [key for key in rows[0].keys() if not key.startswith("source_")]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_sources_markdown(
    path: Path,
    transcript_rows: list[dict[str, object]],
    slide_rows: list[dict[str, object]],
    submission_rows: list[dict[str, object]],
    week_html: str,
) -> None:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    transcript_link = absolutize_url(extract_anchor_link(week_html, "Transcript"), CS50_WEEK_URL) or CS50_TRANSCRIPT_URL
    notes_link = absolutize_url(extract_anchor_link(week_html, "Notes"), CS50_WEEK_URL) or CS50_NOTES_URL
    slides_link = absolutize_url(extract_anchor_link(week_html, "Google Slides"), CS50_WEEK_URL)

    lines = [
        "# Public Demo Sources",
        "",
        f"- 生成时间：{generated_at}",
        "- 说明：这套样例用于证明系统可以接入公开来源的真实材料；不替换现有 synthetic competition-demo。",
        "",
        "## 1. 讲课材料来源",
        f"- Week page：{CS50_WEEK_URL}",
        f"- Transcript：{transcript_link}",
        f"- Notes：{notes_link}",
        f"- Google Slides：{slides_link or '未从页面中提取到公开链接'}",
        "- 许可与使用：CS50 官方课程公开页面，仅用于本地课程分析演示和来源说明。",
        "",
        "## 2. 编程提交来源",
        f"- AIZU 官方 recent submissions API：{AIZU_RECENT_URL}",
        "- 说明：AIZU Online Judge 是 IBM Project CodeNet README 明确列出的两大原始来源之一。",
        "- Project CodeNet README：https://github.com/IBM/Project_CodeNet",
        "- 许可与使用：公开 judge feed，仅提取少量近期 Python3 提交的元数据，不下载源码。",
        "",
        "## 3. 字段转换说明",
        "- transcript_demo.csv",
        "  - 原始字段：CS50 transcript 文本段落",
        "  - 派生字段：start_minute / end_minute 基于段落词数与 150 wpm 语速估算",
        "  - 行数：{}".format(len(transcript_rows)),
        "- ppt_timeline_demo.csv",
        "  - 原始字段：CS50 Notes 页面的 h2 section headings",
        "  - 派生字段：start_minute / end_minute 通过 transcript 段落分桶对齐得到",
        "  - 行数：{}".format(len(slide_rows)),
        "- submission_demo.csv",
        "  - 原始字段：AIZU API 的 judgeId / userId / problemId / problemTitle / status / submissionDate / language",
        "  - 派生字段：student_code / student_name 进行了匿名化；event_minute 映射到课堂练习时间窗",
        "  - 行数：{}".format(len(submission_rows)),
        "",
        "## 4. 主题一致性说明",
        "- 本 public-demo 以 CS50 Python Week 2 Loops 作为讲课材料主线。",
        "- AIZU 选取的是 ITP1 初级题目中的条件判断与循环类 Python3 提交记录，作为“真实编程提交证据”补充。",
        "- 因为公开来源中没有现成的单课堂 quiz / interaction 响应日志，本样例只导入 transcript + ppt_timeline + submission。",
        "- 系统规则评分会按既有设计将缺失的 quiz / interaction 信号按 0 处理。",
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def extract_anchor_link(html_text: str, label: str) -> str | None:
    pattern = re.compile(
        rf"<a[^>]+href=\"([^\"]+)\"[^>]*>\s*{re.escape(label)}\s*</a>",
        flags=re.IGNORECASE,
    )
    match = pattern.search(html_text)
    return match.group(1) if match else None


def absolutize_url(url: str | None, base_url: str) -> str | None:
    if not url:
        return None
    return parse.urljoin(base_url, url)


if __name__ == "__main__":
    raise SystemExit(main())
