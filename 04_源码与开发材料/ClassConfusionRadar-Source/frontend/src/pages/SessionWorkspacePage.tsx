/**
 * 本文件的作用是：组织 SessionWorkspacePage 页面所需的数据加载与界面结构。
 */
import { useEffect, useMemo, useState } from "react";
import { Alert, App, Badge, Button, Result, Skeleton, Space, Tabs, Tooltip, Typography } from "antd";
import { useParams } from "react-router-dom";
import { getAnalyticsOverview, getSegmentAnalytics, runAnalytics } from "../api/analytics";
import { getSession } from "../api/sessions";
import { MetricStrip } from "../components/MetricStrip";
import { SectionSurface } from "../components/SectionSurface";
import { SessionStatusTag } from "../components/StatusTag";
import { ApiIntegrationPanel } from "../features/analytics/ApiIntegrationPanel";
import { AnalyticsDashboard } from "../features/analytics/AnalyticsDashboard";
import { SegmentDetailDrawer } from "../features/analytics/SegmentDetailDrawer";
import { SegmentManager } from "../features/segments/SegmentManager";
import { SuggestionPanel } from "../features/suggestions/SuggestionPanel";
import { UploadPanel } from "../features/uploads/UploadPanel";
import { BuiltinDatasetFloat } from "../features/uploads/BuiltinDatasetFloat";
import type { AnalyticsOverview, SegmentAnalyticsDetail, SessionDetail } from "../types/api";
import { formatCourseType } from "../utils/labels";

const emptyOverview: AnalyticsOverview = {
  has_analysis: false,
  latest_run_id: null,
  generated_at: null,
  score_formula: "",
  scoring_rules: [],
  summary: {
    average_score: 0,
    high_risk_count: 0,
    critical_count: 0,
    total_segments: 0,
  },
  heatmap_cells: [],
  top_errors: [],
  high_risk_segments: [],
};

export function SessionWorkspacePage() {
  const params = useParams();
  const { message } = App.useApp();
  const sessionId = Number(params.sessionId);
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [overview, setOverview] = useState<AnalyticsOverview>(emptyOverview);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [segmentDetail, setSegmentDetail] = useState<SegmentAnalyticsDetail | null>(null);
  const [activeTab, setActiveTab] = useState("overview");

  const print_current_section = (section_id: string) => {
    const target = document.getElementById(section_id);
    if (!target) return;

    // 使用独立副本打印当前板块，避免隐藏元素继续占用分页空间。
    const print_copy = target.cloneNode(true) as HTMLElement;
    print_copy.removeAttribute("id");
    print_copy.classList.add("print-section-copy");

    // cloneNode 不会复制 canvas 像素，需要逐个重绘图表画布。
    const source_canvases = target.querySelectorAll("canvas");
    const copied_canvases = print_copy.querySelectorAll("canvas");
    source_canvases.forEach((source_canvas, index) => {
      const copied_canvas = copied_canvases[index];
      if (!copied_canvas) return;
      copied_canvas.width = source_canvas.width;
      copied_canvas.height = source_canvas.height;
      copied_canvas.getContext("2d")?.drawImage(source_canvas, 0, 0);
    });

    document.body.appendChild(print_copy);

    const cleanup = () => {
      document.body.classList.remove("print-section-active");
      print_copy.remove();
    };

    document.body.classList.add("print-section-active");
    window.addEventListener("afterprint", cleanup, { once: true });
    window.print();
  };

  const reload_workspace = async () => {
    try {
      setLoading(true);
      setPageError(null);
      const [session_detail, analytics_overview] = await Promise.all([
        getSession(sessionId),
        getAnalyticsOverview(sessionId),
      ]);
      setSession(session_detail);
      setOverview(analytics_overview);
    } catch (error) {
      const next_error = (error as Error).message;
      setPageError(next_error);
      message.error(next_error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!Number.isFinite(sessionId)) {
      return;
    }
    void reload_workspace();
  }, [sessionId]);

  const successful_upload_count = session?.uploaded_files.filter((item) => item.parse_status === "success").length ?? 0;
  const failed_upload_count = session?.uploaded_files.filter((item) => item.parse_status === "failed").length ?? 0;
  const can_run_analysis = session ? successful_upload_count > 0 && session.segment_count > 0 : false;
  const top_risk_segment = overview.high_risk_segments[0] ?? null;

  const readiness_hints = useMemo(() => {
    if (!session) {
      return [];
    }

    const hints: string[] = [];
    if (successful_upload_count === 0) {
      hints.push("至少上传并成功解析 1 个课堂数据文件");
    }
    if (session.segment_count === 0) {
      hints.push("至少创建 1 个教学分段");
    }
    return hints;
  }, [session, successful_upload_count]);

  const metrics = useMemo(() => {
    if (!session) {
      return [];
    }
    return [
      {
        label: "成功上传文件",
        value: `${successful_upload_count}/${session.upload_count}`,
        help: failed_upload_count > 0 ? `其中有 ${failed_upload_count} 个文件解析失败` : "建议上传 3 类结构化数据",
      },
      { label: "知识点", value: session.knowledge_point_count, help: "按本节课教学目标组织" },
      { label: "教学分段", value: session.segment_count, help: "按时间与知识点切分" },
      {
        label: "高风险分段",
        value: overview.summary.high_risk_count,
        help: overview.has_analysis ? "可直接进入教学建议页生成建议" : "完成分析后自动统计",
        percent: overview.summary.average_score,
      },
    ];
  }, [failed_upload_count, overview.has_analysis, overview.summary.average_score, overview.summary.high_risk_count, session, successful_upload_count]);

  const workflow_stages = useMemo(() => {
    if (!session) return [];
    return [
      { key: "uploads", number: 1, title: "课堂数据", value: successful_upload_count > 0 ? `${successful_upload_count} 个已解析` : "待上传", done: successful_upload_count > 0 },
      { key: "segments", number: 2, title: "教学分段", value: session.segment_count > 0 ? `${session.segment_count} 个分段` : "待构建", done: session.segment_count > 0 },
      { key: "analytics", number: 3, title: "困惑分析", value: overview.has_analysis ? `均分 ${overview.summary.average_score}` : "待分析", done: overview.has_analysis },
      { key: "suggestions", number: 4, title: "建议与报告", value: overview.has_analysis ? `${overview.summary.high_risk_count} 个高风险` : "等待分析", done: overview.has_analysis },
    ];
  }, [overview.has_analysis, overview.summary.average_score, overview.summary.high_risk_count, session, successful_upload_count]);

  const next_action = useMemo(() => {
    if (!session) return null;
    if (successful_upload_count === 0) return { label: "去上传数据", tab: "uploads", type: "default" as const };
    if (session.segment_count === 0) return { label: "去构建分段", tab: "segments", type: "default" as const };
    if (!overview.has_analysis) return { label: "运行困惑分析", tab: "analytics", type: "analysis" as const };
    if (overview.high_risk_segments.length > 0) return { label: "查看教学建议", tab: "suggestions", type: "default" as const };
    return { label: "查看分析报告", tab: "analytics", type: "default" as const };
  }, [overview.has_analysis, overview.high_risk_segments.length, session, successful_upload_count]);

  const open_segment_detail = async (segmentId: number) => {
    try {
      setDetailOpen(true);
      setDetailLoading(true);
      setSegmentDetail(await getSegmentAnalytics(segmentId));
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setDetailLoading(false);
    }
  };

  const run_confusion_analysis = async () => {
    if (!can_run_analysis) {
      message.warning(`运行分析前，请先完成：${readiness_hints.join("、")}。`);
      return;
    }

    try {
      setRunning(true);
      await runAnalytics(sessionId);
      message.success("课堂分析已完成。");
      setActiveTab("analytics");
      await reload_workspace();
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setRunning(false);
    }
  };

  if (!Number.isFinite(sessionId)) {
    return (
      <Result
        status="404"
        title="课堂场次不存在"
        subTitle="当前链接中的 sessionId 无效，请返回首页重新进入。"
      />
    );
  }

  if (loading) {
    return <Skeleton active paragraph={{ rows: 8 }} />;
  }

  if (pageError && !session) {
    return (
      <Result
        status="error"
        title="课堂工作台加载失败"
        subTitle={pageError}
        extra={
          <Button type="primary" onClick={() => void reload_workspace()}>
            重新加载
          </Button>
        }
      />
    );
  }

  if (!session) {
    return <Result status="404" title="未找到该课堂场次" />;
  }

  return (
    <div className="page-stack">
      <section className="workspace-hero soft-fade">
        <div className="hero-grid">
          <div>
            <Space align="center">
              <Typography.Title style={{ marginBottom: 0 }}>{session.title}</Typography.Title>
              <SessionStatusTag status={session.status} />
            </Space>
            <Typography.Paragraph className="hero-copy">
              {formatCourseType(session.course_type)} · {session.class_date} · {session.duration_minutes} 分钟
              {session.notes ? ` · ${session.notes}` : ""}
            </Typography.Paragraph>
            <div className="hero-actions">
              <Tooltip title={can_run_analysis ? "" : `运行分析前需先完成：${readiness_hints.join("、")}`}>
                <Button type="primary" size="large" loading={running} disabled={!can_run_analysis} onClick={run_confusion_analysis}>
                  运行困惑分析
                </Button>
              </Tooltip>
              <Button size="large" onClick={() => void reload_workspace()}>
                刷新工作台
              </Button>
            </div>
          </div>
          <MetricStrip items={metrics} />
        </div>
      </section>

      <Alert
        type={!can_run_analysis ? "info" : !overview.has_analysis ? "success" : top_risk_segment ? "warning" : "success"}
        showIcon
        message={
          !can_run_analysis
            ? `下一步：${readiness_hints[0] ?? "补充课堂数据"}`
            : !overview.has_analysis
              ? "课堂数据已经准备好，可以开始分析"
              : top_risk_segment
                ? `当前优先关注：${top_risk_segment.title}`
                : "本次分析已完成，当前没有高风险分段"
        }
        description={
          !can_run_analysis
            ? "完成当前步骤后，工作台会自动解锁下一步。"
            : !overview.has_analysis
              ? "运行后会生成困惑热力图、高风险分段和课堂报告。"
              : top_risk_segment
                ? top_risk_segment.overall_explanation
                : "可以继续查看热力图、分段详情和课堂报告。"
        }
        action={next_action ? (
          <Button
            size="small"
            type={next_action.type === "analysis" ? "primary" : "default"}
            loading={next_action.type === "analysis" && running}
            onClick={() => next_action.type === "analysis" ? void run_confusion_analysis() : setActiveTab(next_action.tab)}
          >
            {next_action.label}
          </Button>
        ) : undefined}
      />

      {failed_upload_count > 0 ? (
        <Alert
          type="warning"
          showIcon
          message={`有 ${failed_upload_count} 个上传文件解析失败`}
          description="你可以在“数据上传”页查看具体错误信息，修正文件后重新上传。"
        />
      ) : null}

      <SectionSurface
        title="课堂处理流程"
        description="四个步骤只保留状态和关键数字，点击即可切换到对应页面。"
      >
        <div className="workflow-compact">
          {workflow_stages.map((stage) => (
            <button
              key={stage.key}
              type="button"
              className={`workflow-stage ${stage.done ? "workflow-stage-done" : ""} ${activeTab === stage.key ? "workflow-stage-active" : ""}`}
              onClick={() => setActiveTab(stage.key)}
            >
              <span className="workflow-stage-number">{stage.number}</span>
              <span className="workflow-stage-copy">
                <strong>{stage.title}</strong>
                <small>{stage.value}</small>
              </span>
            </button>
          ))}
        </div>
      </SectionSurface>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: "overview",
            label: "概览",
            children: (
              <div className="page-stack">
                <SectionSurface title="课堂摘要" description="只展示当前状态和下一步，不重复堆叠流程说明。">
                  <div className="overview-focus-card">
                    <div>
                      <Typography.Text type="secondary">当前状态</Typography.Text>
                      <Typography.Title level={4} style={{ marginTop: 4 }}>
                        {overview.has_analysis ? "课堂分析已完成" : can_run_analysis ? "数据准备完成" : "课堂数据准备中"}
                      </Typography.Title>
                      <Typography.Paragraph style={{ marginBottom: 0 }}>
                        已解析 {successful_upload_count} 个文件 · {session.segment_count} 个教学分段
                        {overview.has_analysis ? ` · 平均困惑得分 ${overview.summary.average_score}` : ""}
                      </Typography.Paragraph>
                    </div>
                    {next_action ? (
                      <Button
                        type="primary"
                        loading={next_action.type === "analysis" && running}
                        onClick={() => next_action.type === "analysis" ? void run_confusion_analysis() : setActiveTab(next_action.tab)}
                      >
                        {next_action.label}
                      </Button>
                    ) : null}
                  </div>
                </SectionSurface>
              </div>
            ),
          },
          {
            key: "uploads",
            label: (
              <span>
                数据上传
                <Badge
                  count={failed_upload_count > 0 ? failed_upload_count : session.upload_count}
                  size="small"
                  style={{ marginInlineStart: 8, backgroundColor: failed_upload_count > 0 ? "#d94841" : "#d6b07d" }}
                />
              </span>
            ),
            children: (
              <SectionSurface title="上传课堂数据" description="支持 CSV/XLSX，上传后会立即解析并写入分析库。">
                <UploadPanel sessionId={session.id} files={session.uploaded_files} onRefresh={reload_workspace} />
              </SectionSurface>
            ),
          },
          {
            key: "segments",
            label: (
              <span>
                教学分段
                <Badge count={session.segment_count} size="small" style={{ marginInlineStart: 8, backgroundColor: "#d6b07d" }} />
              </span>
            ),
            children: (
              <SectionSurface
                title="构建教学分段"
                description="先维护知识点，再按时间切分课堂片段，这是 MVP 的核心分析输入。"
              >
                <SegmentManager session={session} onRefresh={reload_workspace} />
              </SectionSurface>
            ),
          },
          {
            key: "analytics",
            label: (
              <span>
                困惑分析
                <Badge
                  count={overview.summary.high_risk_count}
                  size="small"
                  style={{ marginInlineStart: 8, backgroundColor: overview.summary.high_risk_count > 0 ? "#d94841" : "#d6b07d" }}
                />
              </span>
            ),
            children: (
              <div id="print-analytics">
                <SectionSurface
                  title="课堂困惑雷达"
                  description="通过热力图、错误统计和分段明细，帮助教师快速定位群体困惑时刻。"
                  extra={<Button className="print-action" onClick={() => print_current_section("print-analytics")}>打开打印版 / 另存 PDF</Button>}
                >
                  <AnalyticsDashboard
                    sessionId={session.id}
                    overview={overview}
                    onInspectSegment={open_segment_detail}
                    onOpenSuggestions={() => setActiveTab("suggestions")}
                  />
                </SectionSurface>
              </div>
            ),
          },
          {
            key: "api-integration",
            label: "课堂解读",
            children: (
              <div id="print-interpretation">
                <SectionSurface
                  title="课堂解读"
                  description="把评分、错误和课堂材料整理成更容易阅读的结论，帮助教师判断下一步该讲什么。"
                  extra={<Button className="print-action" onClick={() => print_current_section("print-interpretation")}>打开打印版 / 另存 PDF</Button>}
                >
                  <ApiIntegrationPanel
                    sessionId={session.id}
                    overview={overview}
                    onInspectSegment={open_segment_detail}
                  />
                </SectionSurface>
              </div>
            ),
          },
          {
            key: "suggestions",
            label: (
              <span>
                教学建议
                <Badge
                  count={overview.summary.high_risk_count}
                  size="small"
                  style={{ marginInlineStart: 8, backgroundColor: overview.summary.high_risk_count > 0 ? "#d94841" : "#d6b07d" }}
                />
              </span>
            ),
            children: (
              <div id="print-suggestions">
                <SectionSurface
                  title="再教学建议"
                  description="围绕高风险分段整理重讲、追问和巩固建议，方便教师直接复盘和备课。"
                  extra={<Button className="print-action" onClick={() => print_current_section("print-suggestions")}>打开打印版 / 另存 PDF</Button>}
                >
                  <SuggestionPanel highRiskSegments={overview.high_risk_segments} />
                </SectionSurface>
              </div>
            ),
          },
        ]}
      />

      <SegmentDetailDrawer
        open={detailOpen}
        loading={detailLoading}
        detail={segmentDetail}
        onClose={() => setDetailOpen(false)}
      />
      <BuiltinDatasetFloat sessionId={session.id} onRefresh={reload_workspace} />
    </div>
  );
}
