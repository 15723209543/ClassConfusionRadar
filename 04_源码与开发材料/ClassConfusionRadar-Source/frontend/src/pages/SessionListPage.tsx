/**
 * 本文件的作用是：组织 SessionListPage 页面所需的数据加载与界面结构。
 */
import { useEffect, useMemo, useState } from "react";
import { Alert, App, Button, Space, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { deleteSession, listSessions } from "../api/sessions";
import { MetricStrip } from "../components/MetricStrip";
import { SectionSurface } from "../components/SectionSurface";
import { SessionList } from "../features/sessions/SessionList";
import type { SessionSummary } from "../types/api";

const API_DOCS_URL = "http://127.0.0.1:8000/docs";

export function SessionListPage() {
  const { message, modal } = App.useApp();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);

  const loadSessions = async () => {
    try {
      setLoading(true);
      setPageError(null);
      setSessions(await listSessions());
    } catch (error) {
      const nextError = (error as Error).message;
      setPageError(nextError);
      message.error(nextError);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSessions();
  }, []);

  const metrics = useMemo(() => {
    const analyzedCount = sessions.filter((item) => item.status === "analyzed").length;
    const totalRisk = sessions.reduce((acc, item) => acc + item.high_risk_count, 0);
    const demoReadyCount = sessions.filter((item) => item.status === "analyzed" && item.high_risk_count > 0).length;
    return [
      { label: "课堂场次数", value: sessions.length, help: "当前系统中的全部课堂" },
      { label: "已完成分析", value: analyzedCount, help: "完成困惑评分的课堂数量" },
      { label: "累计高风险分段", value: totalRisk, help: "用于展示再教学价值" },
      { label: "需要优先复盘", value: demoReadyCount, help: "已分析且存在高风险分段的课堂" },
    ];
  }, [sessions]);

  const handleDelete = (sessionId: number) => {
    modal.confirm({
      title: "删除课堂场次",
      content: "删除后会同时移除上传数据、分段结果和分析记录。",
      okText: "确认删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await deleteSession(sessionId);
          message.success("课堂场次已删除。");
          await loadSessions();
        } catch (error) {
          message.error((error as Error).message);
        }
      },
    });
  };

  return (
    <div className="page-stack">
      <section className="workspace-hero soft-fade">
        <div className="hero-grid">
          <div>
            <Typography.Text className="eyebrow-text">教师工作台</Typography.Text>
            <Typography.Title>用一节课的数据，定位群体困惑时刻</Typography.Title>
            <Typography.Paragraph className="hero-copy">
              为编程课堂提供一套清晰的教师工作流：创建课堂、上传结构化数据、按知识点分段、运行困惑分析，并直接生成针对高风险分段的再教学建议。
            </Typography.Paragraph>
            <div className="hero-actions">
              <Button size="large" href={API_DOCS_URL} target="_blank">
                API 文档
              </Button>
              <Button type="primary" size="large" onClick={() => navigate("/sessions/new")}>
                新建课堂场次
              </Button>
              <Button size="large" onClick={() => void loadSessions()}>
                刷新列表
              </Button>
            </div>
          </div>
          <MetricStrip items={metrics} />
        </div>
      </section>

      {pageError ? (
        <Alert
          type="error"
          showIcon
          message="课堂列表加载失败"
          description={pageError}
          action={
            <Button size="small" onClick={() => void loadSessions()}>
              重新加载
            </Button>
          }
        />
      ) : null}

      <SectionSurface
        title="课堂工作台列表"
        extra={
          <Space>
            <Button onClick={() => void loadSessions()}>刷新</Button>
            <Button type="primary" onClick={() => navigate("/sessions/new")}>
              新建场次
            </Button>
          </Space>
        }
      >
        <SessionList sessions={sessions} loading={loading} onDelete={handleDelete} />
      </SectionSurface>
    </div>
  );
}
