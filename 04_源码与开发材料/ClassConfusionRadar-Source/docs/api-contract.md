# API 速查

基础路径：`/api/v1`

## 课堂

- `GET /sessions`
- `POST /sessions`
- `GET /sessions/{session_id}`
- `PATCH /sessions/{session_id}`
- `DELETE /sessions/{session_id}`

## 文件与数据包

- `GET /sessions/{session_id}/files`
- `POST /sessions/{session_id}/files`
- `POST /sessions/{session_id}/dataset-zip`
- `DELETE /files/{file_id}`

## 知识点和分段

- `GET /sessions/{session_id}/knowledge-points`
- `POST /sessions/{session_id}/knowledge-points`
- `PATCH /knowledge-points/{knowledge_point_id}`
- `DELETE /knowledge-points/{knowledge_point_id}`
- `GET /sessions/{session_id}/segments`
- `POST /sessions/{session_id}/segments`
- `POST /sessions/{session_id}/segments/auto-build`
- `PATCH /segments/{segment_id}`
- `DELETE /segments/{segment_id}`

## 分析与报告

- `POST /sessions/{session_id}/analytics/run`
- `GET /sessions/{session_id}/analytics/overview`
- `GET /segments/{segment_id}/analytics`
- `GET /sessions/{session_id}/analytics/report.md`
- `GET /sessions/{session_id}/analytics/report.html`

## 再教学

- `POST /segment-scores/{segment_score_id}/suggestions`
- `GET /segment-scores/{segment_score_id}/suggestions`
- `POST /segment-scores/{segment_score_id}/interventions`
- `GET /segment-scores/{segment_score_id}/interventions/latest`
- `POST /interventions/{intervention_id}/verify`

## 增强分析

- `POST /sessions/{session_id}/analytics/enhance`
- `GET /sessions/{session_id}/analytics/enhance`
- `POST /segment-scores/{segment_score_id}/analytics/enhance`
- `GET /segment-scores/{segment_score_id}/analytics/enhance`

## 契约检查

后端测试 `tests/api/test_openapi_contract.py` 会读取 `/openapi.json`，检查比赛演示依赖的主要路由是否存在。这里的“契约检查”指实际自动化测试，不再把普通接口约束表述成已经完成的前后端契约测试。
