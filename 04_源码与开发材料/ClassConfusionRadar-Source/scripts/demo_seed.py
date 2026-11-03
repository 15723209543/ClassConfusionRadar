"""
本文件的作用是：向本地数据库写入演示所需的初始化数据。
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import time
import uuid
from pathlib import Path
from urllib import error, request


ROOT_DIR = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT_DIR / "docs" / "samples" / "competition-demo"
DEMO_TITLE = "Competition Demo · Python 条件与循环"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:5173"

DEMO_SESSION_PAYLOAD = {
    "title": DEMO_TITLE,
    "course_type": "python",
    "class_date": "2026-04-13",
    "duration_minutes": 90,
    "notes": "用于比赛答辩的标准演示场次",
}

DEMO_KNOWLEDGE_POINTS = [
    {
        "name": "条件判断",
        "topic_area": "控制流",
        "description": "围绕 if / elif / else 的分支判断与边界条件。",
        "display_order": 1,
    },
    {
        "name": "while 循环",
        "topic_area": "控制流",
        "description": "围绕 while 循环的条件、循环体和变量更新。",
        "display_order": 2,
    },
    {
        "name": "循环边界与调试",
        "topic_area": "调试",
        "description": "围绕 off-by-one、死循环与中间变量检查。",
        "display_order": 3,
    },
]

DEMO_SAMPLE_FILES = [
    ("quiz", SAMPLE_DIR / "quiz_demo.csv"),
    ("submission", SAMPLE_DIR / "submission_demo.csv"),
    ("interaction", SAMPLE_DIR / "interaction_demo.csv"),
    ("transcript", SAMPLE_DIR / "transcript_demo.csv"),
    ("ppt_timeline", SAMPLE_DIR / "ppt_timeline_demo.csv"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed one demo session for Class Confusion Radar.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL.")
    parser.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL, help="Frontend URL for the final link output.")
    parser.add_argument("--run-analytics", action="store_true", help="Run analytics after loading the demo session.")
    parser.add_argument(
        "--generate-suggestions",
        action="store_true",
        help="Generate the first high-risk segment suggestion after analytics.",
    )
    args = parser.parse_args()

    if args.generate_suggestions and not args.run_analytics:
        parser.error("--generate-suggestions 需要和 --run-analytics 一起使用。")

    ensure_sample_files_exist()

    base_url = args.base_url.rstrip("/")
    print("==> 开始准备本地 demo 数据")
    wait_for_backend(base_url)

    existing_session_ids = find_demo_session_ids(base_url)
    for session_id in existing_session_ids:
        print(f"    删除旧 demo 场次：{session_id}")
        api_request("DELETE", f"{base_url}/api/v1/sessions/{session_id}")

    session = api_request("POST", f"{base_url}/api/v1/sessions", json_body=DEMO_SESSION_PAYLOAD)
    session_id = session["id"]
    print(f"    已创建 demo 场次：{session['title']} (id={session_id})")

    for payload in DEMO_KNOWLEDGE_POINTS:
        created = api_request(
            "POST",
            f"{base_url}/api/v1/sessions/{session_id}/knowledge-points",
            json_body=payload,
        )
        print(f"    已创建知识点：{created['name']}")

    for file_kind, file_path in DEMO_SAMPLE_FILES:
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
        print(f"    已运行分析：{analysis['status']}")

        overview = api_request("GET", f"{base_url}/api/v1/sessions/{session_id}/analytics/overview")
        print(
            "    分析摘要："
            f"总分段 {overview['summary']['total_segments']}，"
            f"高风险 {overview['summary']['high_risk_count']}，"
            f"极高风险 {overview['summary']['critical_count']}"
        )

        if args.generate_suggestions and overview["high_risk_segments"]:
            top_segment = overview["high_risk_segments"][0]
            suggestion = api_request(
                "POST",
                f"{base_url}/api/v1/segment-scores/{top_segment['segment_score_id']}/suggestions",
            )
            print(
                f"    已生成建议：{top_segment['title']} -> {suggestion['status']} "
                f"({suggestion['model_name']})"
            )

    print("")
    print("==> Demo 数据已准备完成")
    print(f"    前端首页：{args.frontend_url}")
    print(f"    Demo 场次直达：{args.frontend_url.rstrip('/')}/sessions/{session_id}")
    print("    推荐接下来的 UI 演示动作：运行分析 -> 查看高风险分段 -> 生成教学建议")
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
    missing = [str(path) for _, path in DEMO_SAMPLE_FILES if not path.exists()]
    if missing:
        raise SystemExit(f"缺少 demo 样例文件：{', '.join(missing)}")


def upload_file(url: str, file_kind: str, file_path: Path) -> dict:
    file_bytes = file_path.read_bytes()
    content_type = mimetypes.guess_type(file_path.name)[0] or "text/csv"
    boundary = f"----CodexDemoBoundary{uuid.uuid4().hex}"

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
