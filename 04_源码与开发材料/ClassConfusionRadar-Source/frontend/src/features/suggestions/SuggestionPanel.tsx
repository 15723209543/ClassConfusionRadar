/**
 * 本文件的作用是：实现 SuggestionPanel 对应的前端交互与界面展示。
 */
import { useEffect, useState } from "react";
import { Alert, App, Button, Empty, Space, Spin, Typography } from "antd";
import { ApiError } from "../../api/client";
import { createSuggestion, getSuggestion } from "../../api/suggestions";
import { RiskLevelTag } from "../../components/StatusTag";
import type { ReteachingSuggestion, RiskSegmentItem } from "../../types/api";
import { formatErrorText } from "../../utils/labels";

interface SuggestionPanelProps {
  highRiskSegments: RiskSegmentItem[];
}

function renderSuggestionMarkdown(content: string) {
  const blocks: JSX.Element[] = [];
  let listItems: string[] = [];

  const flushList = () => {
    if (listItems.length === 0) {
      return;
    }
    blocks.push(
      <ul key={`list-${blocks.length}`} className="suggestion-list">
        {listItems.map((item, index) => (
          <li key={`${item}-${index}`}>{formatErrorText(item)}</li>
        ))}
      </ul>,
    );
    listItems = [];
  };

  content.split(/\r?\n/).forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line) {
      flushList();
      return;
    }

    if (line.startsWith("### ")) {
      flushList();
      blocks.push(
        <Typography.Title level={5} key={`h3-${blocks.length}`}>
          {formatErrorText(line.slice(4))}
        </Typography.Title>,
      );
      return;
    }

    if (line.startsWith("## ")) {
      flushList();
      blocks.push(
        <Typography.Title level={4} key={`h2-${blocks.length}`}>
          {formatErrorText(line.slice(3))}
        </Typography.Title>,
      );
      return;
    }

    if (line.startsWith("- ")) {
      listItems.push(formatErrorText(line.slice(2)));
      return;
    }

    flushList();
    blocks.push(
      <Typography.Paragraph key={`p-${blocks.length}`} className="suggestion-content">
        {formatErrorText(line)}
      </Typography.Paragraph>,
    );
  });

  flushList();
  return blocks;
}

function renderStructuredSuggestion(suggestion: ReteachingSuggestion) {
  if (!suggestion.structured_content) {
    return null;
  }

  const { diagnosis, reteach_script, board_plan, micro_exercises, followup_task } = suggestion.structured_content;
  return (
    <div className="suggestion-structured">
      <div className="suggestion-grid">
        <section className="suggestion-card">
          <Typography.Title level={5}>诊断</Typography.Title>
          <Typography.Paragraph className="suggestion-content">{formatErrorText(diagnosis)}</Typography.Paragraph>
        </section>

        <section className="suggestion-card">
          <Typography.Title level={5}>重讲脚本</Typography.Title>
          <ol className="suggestion-list">
            {reteach_script.map((item, index) => (
              <li key={`reteach-${index}`}>{formatErrorText(item)}</li>
            ))}
          </ol>
        </section>

        <section className="suggestion-card">
          <Typography.Title level={5}>板书规划</Typography.Title>
          <ul className="suggestion-list">
            {board_plan.map((item, index) => (
              <li key={`board-${index}`}>{formatErrorText(item)}</li>
            ))}
          </ul>
        </section>

        <section className="suggestion-card">
          <Typography.Title level={5}>微练习</Typography.Title>
          <ul className="suggestion-list">
            {micro_exercises.map((item, index) => (
              <li key={`exercise-${index}`}>{formatErrorText(item)}</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="suggestion-card">
        <Typography.Title level={5}>跟进任务</Typography.Title>
        <Typography.Paragraph className="suggestion-content">{formatErrorText(followup_task)}</Typography.Paragraph>
      </section>
    </div>
  );
}

export function SuggestionPanel({ highRiskSegments }: SuggestionPanelProps) {
  const { message } = App.useApp();
  const [suggestions, setSuggestions] = useState<Record<number, ReteachingSuggestion>>({});
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const recommendedSegment = highRiskSegments[0] ?? null;

  useEffect(() => {
    let cancelled = false;

    const preloadSuggestions = async () => {
      const unloadedSegments = highRiskSegments.filter((segment) => !suggestions[segment.segment_score_id]);
      if (unloadedSegments.length === 0) {
        return;
      }

      const resultEntries = await Promise.allSettled(
        unloadedSegments.map(async (segment) => {
          try {
            const suggestion = await getSuggestion(segment.segment_score_id);
            return [segment.segment_score_id, suggestion] as const;
          } catch (error) {
            if (error instanceof ApiError && error.status === 404) {
              return null;
            }
            throw error;
          }
        }),
      );

      if (cancelled) {
        return;
      }

      const nextSuggestions: Record<number, ReteachingSuggestion> = {};
      resultEntries.forEach((result) => {
        if (result.status === "fulfilled" && result.value) {
          const [segmentScoreId, suggestion] = result.value;
          nextSuggestions[segmentScoreId] = suggestion;
        }
      });

      if (Object.keys(nextSuggestions).length > 0) {
        setSuggestions((current) => ({ ...current, ...nextSuggestions }));
      }
    };

    void preloadSuggestions();
    return () => {
      cancelled = true;
    };
  }, [highRiskSegments, suggestions]);

  if (highRiskSegments.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <Space direction="vertical" size={4}>
            <Typography.Text>当前没有高风险分段，建议先运行分析或补充更多课堂数据。</Typography.Text>
            <Typography.Text type="secondary">当出现高风险分段后，这里会生成可直接给教师使用的重讲建议、板书规划和微练习。</Typography.Text>
          </Space>
        }
      />
    );
  }

  const loadSuggestion = async (segmentScoreId: number, forceGenerate = false) => {
    try {
      setLoadingId(segmentScoreId);

      let suggestion: ReteachingSuggestion;
      if (forceGenerate) {
        suggestion = await createSuggestion(segmentScoreId);
      } else {
        try {
          suggestion = await getSuggestion(segmentScoreId);
        } catch (error) {
          if (error instanceof ApiError && error.status === 404) {
            suggestion = await createSuggestion(segmentScoreId);
          } else {
            throw error;
          }
        }
      }

      setSuggestions((current) => ({ ...current, [segmentScoreId]: suggestion }));

      if (suggestion.status === "ready") {
        message.success(forceGenerate ? "教学建议已重新生成。" : "教学建议已准备好。");
      } else if (suggestion.status === "failed") {
        message.warning(suggestion.failure_reason || "教学建议生成失败，请稍后重试。");
      }
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <Space direction="vertical" style={{ width: "100%" }} size={18}>
      {recommendedSegment ? (
        <Alert
          type="warning"
          showIcon
          message={`建议优先处理：${recommendedSegment.title}`}
          description={`${formatErrorText(recommendedSegment.overall_explanation)} 建议先获取这一分段的建议，再继续处理后续高风险分段。`}
        />
      ) : null}

      {highRiskSegments.map((segment) => {
        const suggestion = suggestions[segment.segment_score_id];
        const isLoading = loadingId === segment.segment_score_id;
        const isRecommended = recommendedSegment?.segment_score_id === segment.segment_score_id;
        return (
          <div
            key={segment.segment_score_id}
            className={`section-surface soft-fade ${isRecommended ? "surface-spotlight" : ""}`}
          >
            <Space direction="vertical" style={{ width: "100%" }} size={14}>
              <Space wrap style={{ justifyContent: "space-between", width: "100%" }}>
                <div>
                  <Space wrap style={{ marginBottom: 6 }}>
                    {isRecommended ? <span className="spotlight-chip">优先处理</span> : null}
                    {suggestion?.status === "ready" ? <span className="success-chip">已生成建议</span> : null}
                    {suggestion ? <span className="spotlight-chip">{suggestion.generation_mode_label}</span> : null}
                  </Space>
                  <Typography.Title level={5} style={{ marginBottom: 0 }}>
                    {segment.title}
                  </Typography.Title>
                  <Typography.Text type="secondary">
                    {segment.knowledge_point_name || "未绑定知识点"} · {segment.start_minute} - {segment.end_minute} 分钟
                  </Typography.Text>
                </div>
                <Space>
                  <RiskLevelTag riskLevel={segment.risk_level} />
                  <Typography.Text strong>{segment.confusion_score}</Typography.Text>
                </Space>
              </Space>

              <div className="suggestion-meta-grid">
                <div className="compact-metric">
                  <Typography.Text type="secondary">主要原因</Typography.Text>
                  <Typography.Text strong>{segment.primary_signal_label || "待分析"}</Typography.Text>
                </div>
                <div className="compact-metric">
                  <Typography.Text type="secondary">主错误</Typography.Text>
                  <Typography.Text strong>{formatErrorText(segment.main_error_summary)}</Typography.Text>
                </div>
              </div>

              <Alert
                type="info"
                showIcon
                message="分段诊断上下文"
                description={formatErrorText(segment.overall_explanation)}
              />

              <Space>
                <Button
                  type="primary"
                  loading={isLoading}
                  onClick={() => loadSuggestion(segment.segment_score_id, false)}
                >
                  {suggestion ? "刷新建议" : "生成首版建议"}
                </Button>
                <Button loading={isLoading} onClick={() => loadSuggestion(segment.segment_score_id, true)}>
                  重新生成
                </Button>
              </Space>

              {isLoading ? <Spin /> : null}
              {suggestion?.generated_at ? (
                <Typography.Text type="secondary">
                  生成时间：{suggestion.generated_at} · {suggestion.generation_mode_label}
                </Typography.Text>
              ) : null}

              {suggestion?.status === "failed" ? (
                <Alert
                  type="error"
                  showIcon
                  message="建议生成失败"
                  description={suggestion.failure_reason || "建议生成失败，请稍后重试。"}
                />
              ) : null}

              {suggestion?.status === "ready" && suggestion.structured_content ? (
                <>
                  <Alert type="success" showIcon message="建议已整理成教师可直接使用的课堂动作" />
                  {renderStructuredSuggestion(suggestion)}
                </>
              ) : suggestion?.status === "ready" && suggestion.suggestion_markdown ? (
                <div className="suggestion-markdown">{renderSuggestionMarkdown(suggestion.suggestion_markdown)}</div>
              ) : suggestion?.status === "processing" ? (
                <Typography.Text type="secondary">建议仍在生成中，请稍后刷新或重新获取。</Typography.Text>
              ) : !suggestion ? (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <Space direction="vertical" size={4}>
                      <Typography.Text>建议尚未生成，可点击按钮生成首版再教学策略。</Typography.Text>
                      <Typography.Text type="secondary">生成后会按诊断、重讲脚本、板书规划、微练习和跟进任务分区展示。</Typography.Text>
                    </Space>
                  }
                />
              ) : null}
            </Space>
          </div>
        );
      })}
    </Space>
  );
}
