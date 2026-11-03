"""
本文件的作用是：验证自动教学分段相关功能在典型与异常场景下的行为。
"""
def create_session_with_knowledge_points(client):
    session_response = client.post(
        "/api/v1/sessions",
        json={
            "title": "自动分段测试课堂",
            "course_type": "python",
            "class_date": "2026-04-12",
            "duration_minutes": 90,
        },
    )
    session_id = session_response.json()["id"]

    knowledge_points = []
    for display_order, name in enumerate(["变量赋值", "if 条件判断", "for 循环"], start=1):
        response = client.post(
            f"/api/v1/sessions/{session_id}/knowledge-points",
            json={
                "name": name,
                "topic_area": "Python 基础",
                "display_order": display_order,
            },
        )
        assert response.status_code == 201
        knowledge_points.append(response.json())

    return session_id, knowledge_points


def upload_material_file(client, session_id: int, file_kind: str, filename: str, content: str):
    response = client.post(
        f"/api/v1/sessions/{session_id}/files",
        files={"file": (filename, content, "text/csv")},
        data={"file_kind": file_kind},
    )
    assert response.status_code == 201
    assert response.json()["parse_status"] == "success"
    return response.json()


def test_auto_build_segments_from_transcript_and_ppt(client):
    session_id, knowledge_points = create_session_with_knowledge_points(client)

    upload_material_file(
        client,
        session_id,
        "transcript",
        "transcript.csv",
        (
            "start_minute,end_minute,speaker,text\n"
            "0,5,教师,今天先讲变量赋值和输入输出的基本规则。\n"
            "5,12,教师,接下来重点讲 if 条件判断和分支执行顺序。\n"
            "12,20,教师,然后进入 for 循环，观察循环变量如何变化。\n"
        ),
    )
    upload_material_file(
        client,
        session_id,
        "ppt_timeline",
        "ppt_timeline.csv",
        (
            "slide_index,slide_title,start_minute,end_minute\n"
            "1,变量赋值与输入输出,0,5\n"
            "2,if 条件判断,5,12\n"
            "3,for 循环执行流程,12,20\n"
        ),
    )

    response = client.post(f"/api/v1/sessions/{session_id}/segments/auto-build", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["created_count"] == 3
    assert payload["slide_window_count"] == 3
    assert payload["transcript_chunk_count"] == 3
    assert payload["segments"][0]["title"] == "变量赋值与输入输出"
    assert payload["segments"][0]["knowledge_point_id"] == knowledge_points[0]["id"]
    assert payload["segments"][1]["knowledge_point_id"] == knowledge_points[1]["id"]
    assert payload["segments"][2]["knowledge_point_id"] == knowledge_points[2]["id"]


def test_auto_build_segments_requires_transcript_and_ppt(client):
    session_id, _ = create_session_with_knowledge_points(client)

    upload_material_file(
        client,
        session_id,
        "transcript",
        "transcript.csv",
        "start_minute,end_minute,text\n0,5,只上传 transcript 还不够。\n",
    )

    response = client.post(f"/api/v1/sessions/{session_id}/segments/auto-build", json={})

    assert response.status_code == 400
    assert "ppt_timeline" in response.json()["detail"]


def test_auto_build_segments_requires_replace_when_segments_exist(client):
    session_id, _ = create_session_with_knowledge_points(client)

    client.post(
        f"/api/v1/sessions/{session_id}/segments",
        json={
            "title": "手工分段",
            "start_minute": 0,
            "end_minute": 10,
            "display_order": 1,
        },
    )

    upload_material_file(
        client,
        session_id,
        "transcript",
        "transcript.csv",
        "start_minute,end_minute,text\n0,10,这是自动分段的讲稿内容。\n",
    )
    upload_material_file(
        client,
        session_id,
        "ppt_timeline",
        "ppt_timeline.csv",
        "slide_index,slide_title,start_minute,end_minute\n1,自动分段演示,0,10\n",
    )

    response = client.post(f"/api/v1/sessions/{session_id}/segments/auto-build", json={})
    assert response.status_code == 400
    assert "替换" in response.json()["detail"]

    replace_response = client.post(
        f"/api/v1/sessions/{session_id}/segments/auto-build",
        json={"replace_existing": True},
    )
    assert replace_response.status_code == 200
    assert replace_response.json()["created_count"] == 1


def test_auto_build_merges_adjacent_slides_with_same_knowledge_point(client):
    session_id, knowledge_points = create_session_with_knowledge_points(client)

    upload_material_file(
        client,
        session_id,
        "transcript",
        "transcript.csv",
        (
            "start_minute,end_minute,text\n"
            "0,5,先讲 if 条件判断的基本结构。\n"
            "5,10,继续讲 if 条件判断中的分支顺序。\n"
        ),
    )
    upload_material_file(
        client,
        session_id,
        "ppt_timeline",
        "ppt_timeline.csv",
        (
            "slide_index,slide_title,start_minute,end_minute\n"
            "1,if 条件判断,0,5\n"
            "2,if 条件判断案例,5,10\n"
        ),
    )

    response = client.post(f"/api/v1/sessions/{session_id}/segments/auto-build", json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload["created_count"] == 1
    assert payload["slide_window_count"] == 2
    assert payload["segments"][0]["knowledge_point_id"] == knowledge_points[1]["id"]
    assert payload["segments"][0]["start_minute"] == 0
    assert payload["segments"][0]["end_minute"] == 10
