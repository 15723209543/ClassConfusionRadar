"""
本文件的作用是：向本地数据库写入演示所需的初始化数据。
"""
from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import sys
import time
import uuid
from pathlib import Path
from urllib import error, request


ROOT_DIR = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT_DIR / "docs" / "samples" / "public-demo"
DEMO_TITLE = "Public Demo · CS50 Loops with AIZU Submissions"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:5173"

DEMO_SESSION_PAYLOAD = {
    "title": DEMO_TITLE,
    "course_type": "python",
    "class_date": "2026-04-17",
    "duration_minutes": 60,
    "notes": (
        "公开来源样例：讲课材料来自 CS50 Python Week 2 Loops，提交记录来自 AIZU 官方 judge feed，"
        "字段转换说明见 docs/samples/public-demo/SOURCES.md。"
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed one public-source demo session for Class Confusion Radar.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL.")
    parser.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL, help="Frontend URL for the final link output.")
    parser.add_argument("--run-analytics", action="store_true", help="Run analytics after loading the demo session.")
    parser.add_argument(
        "--generate-enhanced",
        action="store_true",
        help="Generate enhanced session and top-segment analyses after rule analysis.",
    )
    args = parser.parse_args()

    ensure_sample_files_exist()

    base_url = args.base_url.rstrip("/")
    print("==> 开始准备 public demo 数据")
    wait_for_backend(base_url)

    existing_session_ids = find_demo_session_ids(base_url)
    for session_id in existing_session_ids:
        print(f"    删除旧 public demo 场次：{session_id}")
        api_request("DELETE", f"{base_url}/api/v1/sessions/{session_id}")

    session = api_request("POST", f"{base_url}/api/v1/sessions", json_body=DEMO_SESSION_PAYLOAD)
    session_id = session["id"]
    print(f"    已创建 public demo 场次：{session['title']} (id={session_id})")

    knowledge_points = [
        row["slide_title"] for row in read_csv_rows(SAMPLE_DIR / "ppt_timeline_demo.csv")[:6]
    ]
    for display_order, name in enumerate(knowledge_points, start=1):
        created = api_request(
            "POST",
            f"{base_url}/api/v1/sessions/{session_id}/knowledge-points",
            json_body={
                "name": name,
                "topic_area": "公开来源真实样例",
                "description": "由 CS50 Notes 章节标题生成。",
                "display_order": display_order,
            },
        )
        print(f"    已创建知识点：{created['name']}")

    for file_kind, file_path in [
        ("transcript", SAMPLE_DIR / "transcript_demo.csv"),
        ("ppt_timeline", SAMPLE_DIR / "ppt_timeline_demo.csv"),
        ("submission", SAMPLE_DIR / "submission_demo.csv"),
    ]:
        uploaded = upload_file(
            f"{base_url}/api/v1/sessions/{session_id}/files",
            file_kind=file_kind,
            file_path=file_path,
        )
        print(f"    已上传 {file_kind}: {uploaded['original_name']} ({uploaded['parse_status']})")

    auto_build_result = api_request(
        "POST",
        f"{base_url}/api/v1/sessions/{session_id}/segments/auto-build",
        json_body={"replace_existing": False},
    )
    print(f"    已自动生成 {auto_build_result['created_count']} 个教学分段")

    if args.run_analytics:
        analysis = api_request("POST", f"{base_url}/api/v1/sessions/{session_id}/analytics/run")
        print(f"    已运行规则分析：{analysis['status']}")

        overview = api_request("GET", f"{base_url}/api/v1/sessions/{session_id}/analytics/overview")
        print(
            "    分析摘要："
            f"总分段 {overview['summary']['total_segments']}，"
            f"高风险 {overview['summary']['high_risk_count']}，"
            f"极高风险 {overview['summary']['critical_count']}"
        )

        if args.generate_enhanced:
            enhanced_session = api_request(
                "POST",
                f"{base_url}/api/v1/sessions/{session_id}/analytics/enhance",
                json_body={"allow_web_search": True, "include_memory": True},
            )
            print(f"    已生成课堂增强总览：{enhanced_session['status']}")

            top_segment = select_segment_for_enhancement(base_url, overview, auto_build_result["segments"])
            if top_segment:
                enhanced_segment = api_request(
                    "POST",
                    f"{base_url}/api/v1/segment-scores/{top_segment['segment_score_id']}/analytics/enhance",
                    json_body={"allow_web_search": True, "include_memory": True},
                )
                print(
                    "    已生成分段增强分析："
                    f"{enhanced_segment['status']} "
                    f"({top_segment['title']}, 得分 {top_segment['confusion_score']})"
                )

    print("")
    print("==> Public demo 数据已准备完成")
    print(f"    前端首页：{args.frontend_url}")
    print(f"    Public demo 直达：{args.frontend_url.rstrip('/')}/sessions/{session_id}")
    print("    推荐演示动作：运行规则分析 -> 生成 API 增强总览 -> 打开高风险或最高分分段 -> 生成增强详情")
    return 0


def wait_for_backend(base_url: str) -> None:
    health_url = f"{base_url}/health"
    for _ in range(30):
        try:
            api_request("GET", health_url)
            return
        except Exception:
            time.sleep(1)
    raise SystemExit("后端未在预期时间内启动，请先确认 http://127.0.0.1:8000 可访问。")


def find_demo_session_ids(base_url: str) -> list[int]:
    sessions = api_request("GET", f"{base_url}/api/v1/sessions")
    return [item["id"] for item in sessions if item.get("title") == DEMO_TITLE]


def ensure_sample_files_exist() -> None:
    missing = [
        str(path)
        for path in [
            SAMPLE_DIR / "transcript_demo.csv",
            SAMPLE_DIR / "ppt_timeline_demo.csv",
            SAMPLE_DIR / "submission_demo.csv",
            SAMPLE_DIR / "SOURCES.md",
        ]
        if not path.exists()
    ]
    if missing:
        raise SystemExit(f"缺少 public demo 样例文件：{', '.join(missing)}")


def select_segment_for_enhancement(base_url: str, overview: dict, segments: list[dict]) -> dict | None:
    if overview["high_risk_segments"]:
        return overview["high_risk_segments"][0]

    scored_segments: list[dict] = []
    for segment in segments:
        detail = api_request("GET", f"{base_url}/api/v1/segments/{segment['id']}/analytics")
        scored_segments.append(
            {
                "segment_score_id": detail["segment_score_id"],
                "segment_id": detail["segment_id"],
                "title": detail["title"],
                "confusion_score": detail["confusion_score"],
            }
        )

    if not scored_segments:
        return None

    scored_segments.sort(key=lambda item: item["confusion_score"], reverse=True)
    return scored_segments[0]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    rows = []
    with path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows.extend(reader)
    return rows


def upload_file(url: str, file_kind: str, file_path: Path) -> dict:
    file_bytes = file_path.read_bytes()
    content_type = mimetypes.guess_type(file_path.name)[0] or "text/csv"
    boundary = f"----CodexPublicDemoBoundary{uuid.uuid4().hex}"

    body = bytearray()
    append_multipart_field(body, boundary, "file_kind", file_kind.encode("utf-8"))
    append_multipart_file(body, boundary, "file", file_path.name, content_type, file_bytes)
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    return api_request(
        "POST",
        url,
        raw_body=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


def append_multipart_field(buffer: bytearray, boundary: str, field_name: str, value: bytes) -> None:
    buffer.extend(f"--{boundary}\r\n".encode("utf-8"))
    buffer.extend(f'Content-Disposition: form-data; name="{field_name}"\r\n\r\n'.encode("utf-8"))
    buffer.extend(value)
    buffer.extend(b"\r\n")


def append_multipart_file(
    buffer: bytearray,
    boundary: str,
    field_name: str,
    filename: str,
    content_type: str,
    file_bytes: bytes,
) -> None:
    buffer.extend(f"--{boundary}\r\n".encode("utf-8"))
    buffer.extend(
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8")
    )
    buffer.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
    buffer.extend(file_bytes)
    buffer.extend(b"\r\n")


def api_request(
    method: str,
    url: str,
    json_body: dict | None = None,
    raw_body: bytes | None = None,
    headers: dict[str, str] | None = None,
):
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)

    data = raw_body
    if json_body is not None:
        data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json; charset=utf-8"

    req = request.Request(url, data=data, method=method, headers=request_headers)
    try:
        with request.urlopen(req, timeout=20) as response:
            payload = response.read()
            if not payload:
                return None
            return json.loads(payload.decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        try:
            parsed = json.loads(detail)
            detail_message = parsed.get("detail") or parsed
        except json.JSONDecodeError:
            detail_message = detail
        raise RuntimeError(f"{method} {url} 失败：{detail_message}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"无法访问 {url}：{exc.reason}") from exc


if __name__ == "__main__":
    sys.exit(main())
