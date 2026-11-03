# Class Confusion Radar / 课堂困惑雷达

一个基于 **React 18、TypeScript、Vite、FastAPI和SQLite（本地）或 PostgreSQL（Docker）** 构建的面向教师的课堂分析 Web 应用。网站主要面向高校程序设计课程教师，用于解决课堂多源数据分散、困惑难定位与再教学缺少效果核验，并提供课堂数据导入与教学内容自动分段、多信号困惑评分及证据解释、再教学建议与后续效果核验等能力。


> **特别说明：**
>
> <strong>竞赛获奖：</strong>本作品已获 <strong>安徽省大数据与人工智能大赛创意组省级三等奖、iCAN 大学生创新创业大赛创新赛道安徽赛区省级二等奖</strong>。<br><strong>软件著作权：</strong>据项目团队确认，本作品<strong>已取得软件著作权</strong>，并非可随意冒名使用的无主作品。<br><strong>权利与竞赛诚信：</strong>严禁抄袭、删改署名、冒充原创，或未经许可将原项目或以其为主要基础的作品用于其他竞赛、成果申报、软件著作权申请及商业用途。查看、学习、修改和传播的具体权限与限制，均以根目录 [`LICENSE.md`](./LICENSE.md) 为准。<br>


---

## 1. 版本与项目信息

| 项目 | 内容 |
| --- | --- |
| 中文名称 | 课堂困惑雷达 |
| 英文名称 | Class Confusion Radar |
| 当前版本 | **v1.0** |
| 发布日期 | 2026-11-02 |
| 网站类型 | 本地 Web 应用（附 Windows EXE 演示启动器） |
| 前端技术 | React 18 + TypeScript + Vite + Ant Design + ECharts |
| 后端或服务 | Python FastAPI、SQLAlchemy、Alembic；可选 OpenAI 兼容接口 |
| 数据存储 | 本地 SQLite / Docker PostgreSQL；上传文件使用本地目录 |
| 运行方式 | Windows EXE 本地启动、前后端源码开发或 Docker Compose |
| 默认访问方式 | 本地 EXE 模式 `http://127.0.0.1:8000`；前端源码模式 `http://127.0.0.1:5173`；未提供已部署的公网网站 |
| 项目入口 | `frontend/src/main.tsx；backend/app/main.py；desktop_launcher.py` |
| 当前状态 | 可供本地演示；本次核验为静态源码与材料审阅，未在当前环境运行 Windows EXE |

---

## 2. 网站简介

本项目面向高校程序设计课程教师，尝试解决课堂测验、代码提交、互动、讲稿和 PPT 时间轴等多源信息分散的问题。<br><strong>核心流程：</strong>导入五类数据 → 按真实授课时间窗自动分段 → 计算可解释的困惑得分、风险等级、证据完整度和典型错误 → 提供再教学建议 → 在后续同知识点课堂中核验干预效果。<br><strong>交付形态：</strong>浏览器教师工作台、前后端源码、Windows 本地 EXE 启动器及合成演示数据；目前主要用于本地演示和课堂试用。

## 3. 核心功能

### 3.1 用户侧功能

<strong>01｜课堂管理：</strong>创建课堂、进入课堂工作台。<br><strong>02｜数据导入：</strong>分别上传测验、代码提交、互动、讲稿及 PPT 时间轴等 CSV / Excel 文件，或使用 ZIP 一键导入。<br><strong>03｜知识点与分段：</strong>维护知识点，按课件时间窗自动分段，也支持人工调整。<br><strong>04｜困惑分析：</strong>运行评分，查看风险热力图、数据完整度、贡献证据和典型错误。<br><strong>05｜教学建议：</strong>获取再教学建议并记录是否采纳、实际干预内容。<br><strong>06｜后续核验：</strong>对后续课堂同知识点复评，比较干预前后分数。<br><strong>07｜结果导出：</strong>支持 Markdown 分析报告和可打印的 HTML 报告。

### 3.2 搜索、推荐、匹配或其他核心业务

<strong>自动分段：</strong>按 PPT 实际翻页时间窗匹配讲稿，合并连续同知识点片段。<br><strong>困惑评分：</strong>测验错误率 35%、提交失败率 35%、重复错误密度 20%、互动沉默度 10%；仅对存在证据的信号权重重新归一化。<br><strong>可解释性：</strong>单独展示风险得分与数据完整度，并显示典型错误及信号贡献。<br><strong>干预核验：</strong>对比后续同知识点课堂的分析结果，反馈教学改进效果。

---

## 4. 技术栈与整体架构

<strong>前端：</strong>React 18、TypeScript、Vite、Ant Design、ECharts。<br><strong>后端：</strong>Python、FastAPI、Uvicorn、SQLAlchemy、Alembic。<br><strong>存储：</strong>本地 SQLite + 文件目录；Docker 演示方案支持 PostgreSQL 15。<br><strong>测试：</strong>后端 pytest、前端 Vitest（仓库具备测试代码，未在本次环境执行）。<br><strong>交付与启动：</strong>Windows EXE 启动器；另有源码启动和 Docker Compose 方案。

### 4.1 前端

<strong>路由：</strong>`frontend/src/routes/index.tsx` 定义课堂列表、课堂创建和课堂工作台。<br><strong>页面与模块：</strong>`frontend/src/pages/`、`frontend/src/features/`。<br><strong>接口客户端：</strong>`frontend/src/api/` 统一调用后端 HTTP API。<br><strong>可视化：</strong>Ant Design 页面组件、ECharts 分析图表。

### 4.2 后端或服务端

<strong>应用入口：</strong>`backend/app/main.py` 创建 FastAPI 应用。<br><strong>API：</strong>`backend/app/api/v1/routes/` 提供课堂、文件、知识点、分段、分析和建议等接口。<br><strong>业务服务：</strong>`backend/app/services/` 处理数据导入、自动分段、评分、建议与核验；AI 增强是可选模块。<br><strong>前端托管：</strong>存在 `frontend/dist` 时，后端可提供已构建的前端页面。<br><strong>鉴权现状：</strong>当前源码未呈现独立的用户登录鉴权流程。

### 4.3 数据与存储

<strong>数据库模型：</strong>SQLAlchemy ORM 保存课堂、知识点、教学片段、学生匿名标识、分析得分、建议及干预记录。<br><strong>上传文件：</strong>保存到配置项 `STORAGE_DIR` 指向的本地目录。<br><strong>Windows 本地模式：</strong>EXE 启动器在程序旁的 `app_data/` 下建立 SQLite 数据库、上传目录和日志。

### 4.4 第三方服务

<strong>默认模式：</strong>`AI_PROVIDER=offline`，离线规则建议无需外部接口。<br><strong>可选增强：</strong>自行配置兼容 OpenAI API 的模型地址、模型名和 API Key 才会启用。<br><strong>评分原则：</strong>困惑分数由本地可解释规则计算，不允许由大模型改写。

---

## 5. 快速开始与部署

### 5.1 本地运行

<strong>仓库地址：</strong>`https://github.com/15723209543/ClassConfusionRadar`；此前检查该仓库尚未推送源码，若仍为空，请先使用项目交付 ZIP 中的文件。<br><strong>Windows EXE 演示：</strong>双击交付包中的 `03_可运行程序/ClassConfusionRadar.exe`，在浏览器访问 `http://127.0.0.1:8000`。<br><strong>后端源码（先进入 `ClassConfusionRadar-Source/backend`）：</strong><br>① `py -m pip install -e ".[dev]"`<br>② `py -m alembic upgrade head`<br>③ `py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`<br><strong>前端源码（另开终端进入 `ClassConfusionRadar-Source/frontend`）：</strong><br>① `npm ci`<br>② `npm run dev`<br>③ 浏览器打开 `http://127.0.0.1:5173`。<br><strong>Docker 演示：</strong>源码中附带 `Run.bat` / `Stop.bat` 启停脚本及 `docker-compose.yml`。<br><strong>目录提示：</strong>压缩包内源码位于 `04_源码与开发材料/ClassConfusionRadar-Source/`；以上命令根据静态文件审阅整理，未在本次环境实际启动。

### 5.2 环境变量与配置

<strong>配置文件：</strong>参照根目录、`backend/`、`frontend/` 的 `.env.example`。<br><strong>数据库与文件：</strong>`DATABASE_URL`、`STORAGE_DIR`。<br><strong>跨域与前端地址：</strong>`CORS_ORIGINS`、`VITE_API_BASE_URL`。<br><strong>匿名和导入限制：</strong>`ANONYMIZE_STUDENTS`、`PRIVACY_SALT`、`MAX_DATASET_ZIP_MB`。<br><strong>可选 AI：</strong>`AI_PROVIDER`、`AI_API_KEY`、`AI_BASE_URL`、`AI_MODEL`。<br>不要公开真实 `.env`、密钥、隐私盐值或生产数据库连接串。

### 5.3 常见启动问题

<strong>端口冲突：</strong>后端默认 8000、源码前端默认 5173；检查端口是否被占用。<br><strong>未自动打开网页：</strong>Windows EXE 启动后可手动访问 `http://127.0.0.1:8000`；可通过 `CCR_PORT` 修改服务端口。<br><strong>前后端无法通信：</strong>核对 `.env.example`、接口地址及跨域配置。<br><strong>EXE 安全提示：</strong>核验文件来源，不建议永久关闭防火墙或杀毒保护。

---

## 6. 页面与用户流程

### 6.1 主要页面

<strong>`/`：</strong>课堂列表。<br><strong>`/sessions/new`：</strong>创建课堂。<br><strong>`/sessions/:sessionId`：</strong>课堂工作台，提供导入、分段、分析、建议和效果核验。<br><strong>`/docs`：</strong>后端生成的 OpenAPI 文档。

### 6.2 典型用户流程

<strong>第 1 步：</strong>进入课堂列表并创建课堂。<br><strong>第 2 步：</strong>导入测验、提交、互动、讲稿与 PPT 时间轴。<br><strong>第 3 步：</strong>对齐讲解时间轴，建立知识点分段并运行困惑评分。<br><strong>第 4 步：</strong>查看高风险片段、证据、错误样例和再教学建议。<br><strong>第 5 步：</strong>记录采纳，在后续课堂用相同知识点核验变化。

---

## 7. API 接口说明

### 7.1 接口概览

<strong>API 前缀：</strong>`/api/v1`。<br><strong>课堂管理</strong><br>• `GET /sessions` — 获取课堂列表。<br>• `POST /sessions` — 创建课堂。<br><strong>数据上传与教学分段</strong><br>• `POST /sessions/{session_id}/files` — 上传文件。<br>• `POST /sessions/{session_id}/dataset-zip` — 一键导入数据 ZIP。<br>• `POST /sessions/{session_id}/segments/auto-build` — 自动分段。<br><strong>评分与结果</strong><br>• `POST /sessions/{session_id}/analytics/run` — 运行困惑评分。<br>• `GET /sessions/{session_id}/analytics/overview` — 查询分析汇总。<br><strong>教学建议与干预</strong><br>• `POST /segment-scores/{segment_score_id}/suggestions` — 生成建议。<br>• `POST /segment-scores/{segment_score_id}/interventions` — 记录干预。<br>• `POST /interventions/{intervention_id}/verify` — 核验效果。<br><strong>完整接口协议：</strong>`docs/api-contract.md`。

---

## 8. 数据文件或数据库说明

### 8.1 主要数据

<strong>`backend/app/models/`：</strong>课堂、学生、文件、知识点、教学片段、困惑得分、教学建议及干预等 ORM 模型。<br><strong>`backend/storage/uploads/`：</strong>上传文件存储目录。<br><strong>`demo_data/`：</strong>用于展示的合成数据。<br><strong>`docs/samples/`：</strong>CSV、JSON 与 ZIP 示例数据。

### 8.2 数据初始化与更新

<strong>源码后端：</strong>在 `backend/` 执行 `py -m alembic upgrade head` 完成迁移。<br><strong>Docker Compose：</strong>后端启动命令包含 `alembic upgrade head`。<br><strong>Windows EXE：</strong>启动器创建本地 SQLite 表和 `app_data/` 数据目录；若数据库没有课堂记录，会尝试导入随包演示数据。

### 8.3 演示数据说明

<strong>批量数据：</strong>20 组测试数据。<br><strong>现场数据：</strong>1 组现场演示数据。<br><strong>数据性质：</strong>说明文件明确标注学生记录为程序合成，并非真实学生档案或真实课堂教学成效；不应用于对实际学生作结论。

---

## 9. 项目结构

<strong>源码主目录：</strong>`ClassConfusionRadar-Source/`<br>├─ `frontend/src/routes/` — 前端路由<br>├─ `frontend/src/pages/` — 课堂列表、创建及工作台页面<br>├─ `frontend/src/features/` — 业务功能面板<br>├─ `frontend/src/api/` — 接口封装<br>├─ `backend/app/api/` — FastAPI 接口路由<br>├─ `backend/app/services/` — 分段、导入、建议和核验<br>├─ `backend/app/analytics/` — 评分算法<br>├─ `backend/app/models/` — 数据模型<br>├─ `backend/alembic/` — 数据库迁移<br>├─ `backend/tests/`、`frontend/tests/` — 测试<br>├─ `demo_data/` — 合成演示数据<br>├─ `docs/` — 接口和评分说明<br>├─ `scripts/` — 构建、启停和演示脚本<br>├─ `desktop_launcher.py` — Windows 本地入口<br>└─ `docker-compose.yml` — 容器化部署方案

---

## 10. 前后端模块与实现思路

### 10.1 前端页面与组件组织

<strong>页面：</strong>`frontend/src/pages/` 包含课堂创建、列表与工作台。<br><strong>功能：</strong>`features/` 按课堂、分段、分析、建议拆分。<br><strong>共享组件：</strong>`components/` 实现指标卡等复用 UI。<br><strong>路由与请求：</strong>`routes/` 声明浏览器路由，`api/` 封装请求。

### 10.2 后端路由与业务模块

<strong>接口层：</strong>`backend/app/api/v1/routes/`。<br><strong>服务层：</strong>`backend/app/services/`，处理数据解析、分段、规则分析、建议和核验。<br><strong>模型层：</strong>`backend/app/models/`，使用 SQLAlchemy ORM。<br><strong>迁移：</strong>`backend/alembic/`。

### 10.3 核心业务算法

<strong>分段：</strong>`segment_builder_service.py` 依据 PPT 时间窗对齐讲稿、合并连续同知识点。<br><strong>评分：</strong>`analytics/scoring.py` 用 35 / 35 / 20 / 10 的四信号权重，只对有证据的信号重新归一化。<br><strong>结果：</strong>风险等级与证据完整度独立呈现，并区分重复错误密度和普通提交失败。

---

## 11. 测试与兼容性

### 11.1 测试

<strong>后端：</strong>`backend/tests/` 有 pytest 的 API、评分、隐私与端到端测试代码，可执行 `py -m pytest`。<br><strong>前端：</strong>`frontend/tests/` 有 Vitest 测试，可执行 `npm test`。<br><strong>执行状态：</strong>本次仅审阅源码与测试文件，未安装依赖或实际执行这些测试，不宣称运行通过。

---

## 12. 当前版本说明

### v1.0


<strong>版本：</strong>v1.0。<br><strong>已具备的源码功能：</strong>课堂管理、五类数据导入、ZIP 导入、时间分段、困惑分析、数据完整度与错误证据、离线建议、后续教学干预核验。<br><strong>交付方式：</strong>Windows 本地 EXE 启动器与 Docker 演示脚本。<br><strong>文档发布日期：</strong>2026-11-02；不据此推断首次开发或比赛日期。


## 13. 后续开发计划

<strong>真实场景：</strong>开展课堂试点并收集教师反馈。<br><strong>系统集成：</strong>后续尝试对接 OJ / LMS 平台。<br><strong>算法改进：</strong>使用真实课堂反馈校准评分权重和风险阈值。<br>上述为答辩材料中的后续规划，不代表 v1.0 已完成。

---

## 14. 已知限制

<strong>部署：</strong>未提供已上线的公网访问地址，主要用于本地演示及课堂试用。<br><strong>兼容：</strong>未提供跨浏览器、跨设备的完整实测记录。<br><strong>集成：</strong>OJ / LMS 自动对接属于后续计划。<br><strong>EXE：</strong>作为本机 Web 服务启动器，界面仍需通过浏览器访问。

---

## 15. 第三方资源与许可证

<strong>前端依赖：</strong>React、Ant Design、ECharts、Vite、Vitest。<br><strong>后端依赖：</strong>FastAPI、SQLAlchemy、Alembic、Uvicorn、pytest。<br><strong>存储与部署：</strong>SQLite；Docker 演示可用 PostgreSQL。<br><strong>许可证：</strong>本次未收到全部第三方许可证清单，不在 README 中猜测各组件协议；第三方作品仍遵守原权利人条款。

本项目自身的授权方式见：[`LICENSE.md`](./LICENSE.md)

---

## 16. 版权与使用声明

- 本项目仅可在仓库根目录 [`LICENSE.md`](./LICENSE.md) 允许的范围内使用、复制、修改、发布、部署或传播。
- 不得删除、隐瞒或篡改项目来源及版权信息，不得将本项目、页面设计、代码或随仓库提供的内容直接冒充为自己的原创成果。
- 对项目进行修改、二次发布、商业使用、重新部署或其他形式再利用时，应遵守 `LICENSE.md` 中的授权要求；需要另行授权的，应事先取得许可。
- 本项目按现状提供，不保证绝对正确、完整、持续可用或适用于特定业务场景。因部署、运行、修改或使用产生的风险与后果，由使用者自行承担。
- 第三方框架、组件、图片、字体、数据或服务仍遵循其各自的许可证、版权规则和服务条款。

以上仅为 README 中的通用提示。具体版权归属、授权范围、使用限制、免责声明及其他约定，均以仓库根目录中的 [`LICENSE.md`](./LICENSE.md) 为准。

---

## 17. 隐私与安全说明

<strong>处理范围：</strong>课堂测验、程序提交、互动、讲稿和课件时间轴。<br><strong>保存位置：</strong>本地 SQLite 或配置数据库；上传文件存于本地目录。<br><strong>匿名：</strong>支持 `ANONYMIZE_STUDENTS` 对学生标识进行匿名化。<br><strong>演示数据：</strong>随包学生记录为合成数据。<br><strong>公开前检查：</strong>删除真实个人资料、`.env`、密码、Token、Cookie、私钥、数据库副本及非必要上传文件。

---

## 18. 联系方式

如需交流项目实现思路或反馈问题，可通过以下邮箱联系：

```text
15723209543@163.com
```

---

## 19. 结语

### <strong>一、项目荣誉与软件著作权</strong><br>

本作品已获 <strong>安徽省大数据与人工智能大赛创意组省级三等奖、iCAN 大学生创新创业大赛创新赛道安徽赛区省级二等奖</strong>

<strong>本作品已取得软件著作权</strong>。这些成果来自项目组的共同工作，不应被他人隐去来源后冒充原创或再次申报。<br><strong>权利提示：</strong>软件著作权与获奖事实不等于向公众无限授权；本项目代码与材料的查看、复制、修改、转载、竞赛参赛、著作权登记申请及商业使用边界，以 [`LICENSE.md`](./LICENSE.md) 为准。

未经许可，不得将本作品或以本作品为主要基础的衍生版本作为本人独立完成的竞赛作品、软件著作权登记成果或商业产品提交。<br><br>

### <strong>二、项目成员与实际分工（依据答辩 PPT）</strong><br>

• <strong>徐培智｜项目负责人：</strong>负责项目整体方案设计、系统架构搭建和核心功能开发；第一阶段辅助开发、第二阶段主要开发；省赛答辩<br>• <strong>韩林默｜项目副负责人：</strong>负责项目整体方案设计、系统架构搭建和核心功能开发；第一阶段主要开发、第二阶段辅助开发；校赛答辩<br>• <strong>林臻阳｜商业分析：</strong>负责使用、录制商业推广视频制作，完成PPT背景和海报图片插入。<br>• <strong>程运杰｜后续开发：</strong>负责下一期开发。<br>• <strong>翁静惠｜替补答辩：</strong>替补答辩，防止出现无人答辩导致弃赛情况。<br><br>

### <strong>三、致谢</strong><br>

衷心感谢<strong>合肥工业大学宣城校区物联网基础实验室姜烨老师</strong>在安徽省大数据与人工智能大赛项目推进过程中给予的指导与帮助。

衷心感谢<strong>合肥工业大学宣城校区电子设计实验室李春华老师</strong>在iCAN 大学生创新创业大赛创新赛项目推进过程中给予的指导与帮助。

同时感谢徐培智、韩林默、林臻阳、程运杰、翁静惠五位项目成员在方案设计、程序开发、功能测试、文档整理与竞赛展示中的付出与协作。

项目荣誉属于团队共同努力的成果，我们尊重每一位成员的真实贡献，也希望使用和引用本作品的人遵守许可条款与学术诚信要求。


