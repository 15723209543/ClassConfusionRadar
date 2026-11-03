/**
 * 本文件的作用是：实现 EnhancedSessionAnalysisPanel 对应的前端交互与界面展示。
 */
import { useEffect, useState } from "react";
import { Alert, App, Button, Empty, List, Space, Spin, Tag, Typography } from "antd";
import { ApiError } from "../../api/client";
import {
  createSessionEnhancedAnalysis,
  getSessionEnhancedAnalysis,
} from "../../api/enhancedAnalytics";
import type { EnhancedSessionAnalysis } from "../../types/api";

interface EnhancedSessionAnalysisPanelProps {
  sessionId: number;
  hasAnalysis: boolean;
  onInspectSegment: (segmentId: number) => void;
}

export function EnhancedSessionAnalysisPanel({
  sessionId,
  hasAnalysis,
  onInspectSegment,
}: EnhancedSessionAnalysisPanelProps) {
  const { message } = App.useApp();
  const [enhancement, setEnhancement] = useState<EnhancedSessionAnalysis | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    if (!hasAnalysis) {
      setEnhancement(null);
      return;
    }

    const loadExisting = async () => {
      try {
        const result = await getSessionEnhancedAnalysis(sessionId);
        if (!cancelled) {
          setEnhancement(result);
        }
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return;
        }
        if (!cancelled) {
          message.error((error as Error).message);
        }
      }
    };

    void loadExisting();
    return () => {
      cancelled = true;
    };
  }, [hasAnalysis, message, sessionId]);

  const handleGenerate = async (forceRefresh: boolean) => {
    try {
      setLoading(true);
      const result = await createSessionEnhancedAnalysis(sessionId, {
        force_refresh: forceRefresh,
        allow_web_search: true,
        include_memory: true,
      });
      setEnhancement(result);
      if (result.status === "ready") {
        message.success(forceRefresh ? "增强总览已重新生成。" : "增强总览已准备完成。");
      } else if (result.status === "failed") {
        message.warning(result.failure_reason || "增强总览生成失败，请稍后重试。");
      }
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (!hasAnalysis) {
    return (
      <Alert
        type="info"
        showIcon
        message="请先完成规则评分"
        description="增强解释建立在现有规则评分结果之上。先运行课堂分析，再生成增强总览。"
      />
    );
  }

  return (
    <div className="analytics-panel">
      <div className="panel-header">
        <div>
          <Typography.Title level={5}>增强解释</Typography.Title>
          <Typography.Text type="secondary">
            不改动热力图和规则分数，只把高风险原因整理成更容易阅读的课堂诊断。
          </Typography.Text>
        </div>
        <Space>
          <Button type="primary" loading={loading} onClick={() => void handleGenerate(false)}>
            {enhancement ? "刷新增强总览" : "生成增强总览"}
          </Button>
          <Button loading={loading} onClick={() => void handleGenerate(true)}>
            重新生成
          </Button>
        </Space>
      </div>

      {loading ? <Spin /> : null}

      {!enhancement ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="当前还没有增强总览，可按需生成。"
        />
      ) : enhancement.status === "failed" ? (
        <Alert
          type="error"
          showIcon
          message="增强总览生成失败"
          description={enhancement.failure_reason || "外部增强分析服务暂不可用，请稍后重试。"}
        />
      ) : enhancement.status === "ready" ? (
        <Space direction="vertical" size={14} style={{ width: "100%" }}>
          <Alert type="success" showIcon message="规则评分保留不变，以下内容为补充解释层。" />
          <Tag>{enhancement.generation_mode_label}</Tag>

          <div className="enhanced-summary-card">
            <Typography.Title level={5}>一句话课堂诊断</Typography.Title>
            <Typography.Paragraph className="suggestion-content">
              {enhancement.summary}
            </Typography.Paragraph>
          </div>

          <div className="enhanced-grid">
            <section className="suggestion-card">
              <Typography.Title level={5}>教师关注重点</Typography.Title>
              <ul className="suggestion-list">
                {enhancement.teacher_takeaways.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            </section>

            <section className="suggestion-card">
              <Typography.Title level={5}>课堂内记忆</Typography.Title>
              {enhancement.memory_notes.length === 0 ? (
                <Typography.Text type="secondary">当前还没有沉淀的课堂内记忆。</Typography.Text>
              ) : (
                <ul className="suggestion-list">
                  {enhancement.memory_notes.map((item, index) => (
                    <li key={`${item}-${index}`}>{item}</li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <section className="suggestion-card">
            <Typography.Title level={5}>高风险分段增强摘要</Typography.Title>
            <List
              dataSource={enhancement.top_segment_insights}
              renderItem={(item) => (
                <List.Item
                  actions={[
                    <Button
                      key="inspect"
                      type="link"
                      disabled={!item.segment_id}
                      onClick={() => item.segment_id && onInspectSegment(item.segment_id)}
                    >
                      查看对应分段
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={item.title}
                    description={
                      <Space direction="vertical" size={4}>
                        <Typography.Text>{item.why_high_risk}</Typography.Text>
                        <Tag color="gold">教师动作：{item.teacher_focus}</Tag>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </section>

          <section className="suggestion-card">
            <Typography.Title level={5}>引用来源</Typography.Title>
            {enhancement.citations.length === 0 ? (
              <Typography.Text type="secondary">当前没有可展示的引用来源。</Typography.Text>
            ) : (
              <List
                dataSource={enhancement.citations}
                renderItem={(item) => (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        item.url ? (
                          <a href={item.url} target="_blank" rel="noreferrer">
                            {item.title}
                          </a>
                        ) : (
                          item.title
                        )
                      }
                      description={
                        <Space direction="vertical" size={2}>
                          <Typography.Text type="secondary">{item.source_type}</Typography.Text>
                          <Typography.Text>{item.excerpt}</Typography.Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </section>
        </Space>
      ) : (
        <Typography.Text type="secondary">增强总览仍在生成中，请稍后刷新。</Typography.Text>
      )}
    </div>
  );
}
