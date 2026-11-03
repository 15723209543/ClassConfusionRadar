/**
 * 本文件的作用是：实现 SegmentDetailDrawer 对应的前端交互与界面展示。
 */
import { useEffect, useState } from "react";
import { Alert, App, Button, Descriptions, Drawer, Empty, List, Progress, Skeleton, Space, Spin, Table, Tag, Typography } from "antd";
import { ApiError } from "../../api/client";
import { createReteachingIntervention, getLatestReteachingIntervention, verifyReteachingIntervention } from "../../api/analytics";
import { createSegmentEnhancedAnalysis, getSegmentEnhancedAnalysis } from "../../api/enhancedAnalytics";
import { RiskLevelTag } from "../../components/StatusTag";
import type { EnhancedSegmentAnalysis, ReteachingInterventionRead, SegmentAnalyticsDetail } from "../../types/api";
import { formatErrorLabel, formatErrorText } from "../../utils/labels";

interface SegmentDetailDrawerProps {
  open: boolean;
  loading: boolean;
  detail: SegmentAnalyticsDetail | null;
  onClose: () => void;
}

export function SegmentDetailDrawer({ open, loading, detail, onClose }: SegmentDetailDrawerProps) {
  const { message } = App.useApp();
  const sortedSignals = detail
    ? [...detail.signal_breakdown].sort((left, right) => right.contribution_score - left.contribution_score)
    : [];
  const primarySignal = sortedSignals.find((item) => item.is_available) ?? null;
  const [enhancement, setEnhancement] = useState<EnhancedSegmentAnalysis | null>(null);
  const [enhancementLoading, setEnhancementLoading] = useState(false);
  const [intervention, setIntervention] = useState<ReteachingInterventionRead | null>(null);
  const [interventionLoading, setInterventionLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    if (!open || !detail) {
      setEnhancement(null);
      return;
    }

    const loadExisting = async () => {
      try {
        const result = await getSegmentEnhancedAnalysis(detail.segment_score_id);
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
  }, [detail, message, open]);

  useEffect(() => {
    let cancelled = false;

    if (!open || !detail) {
      setIntervention(null);
      return;
    }

    const loadIntervention = async () => {
      try {
        const result = await getLatestReteachingIntervention(detail.segment_score_id);
        if (!cancelled) {
          setIntervention(result);
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

    void loadIntervention();
    return () => {
      cancelled = true;
    };
  }, [detail, message, open]);

  const handleRecordIntervention = async () => {
    if (!detail) {
      return;
    }
    try {
      setInterventionLoading(true);
      const result = await createReteachingIntervention(detail.segment_score_id, {
        status: "executed",
        plan_text: `已根据“${detail.title}”分段的困惑分析结果采纳再教学建议。`,
        outcome_summary: "已记录执行，后续可补充复测分数或作业表现变化。",
        followup_score_before: detail.confusion_score,
      });
      setIntervention(result);
      message.success("已记录再教学干预，闭环证据已保存。");
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setInterventionLoading(false);
    }
  };

  const handleVerifyIntervention = async () => {
    if (!intervention) {
      return;
    }
    try {
      setInterventionLoading(true);
      const result = await verifyReteachingIntervention(intervention.id);
      setIntervention(result);
      message.success("已用后续课堂数据完成核验。");
    } catch (error) {
      message.warning((error as Error).message);
    } finally {
      setInterventionLoading(false);
    }
  };

  const handleGenerateEnhancement = async (forceRefresh: boolean) => {
    if (!detail) {
      return;
    }

    try {
      setEnhancementLoading(true);
      const result = await createSegmentEnhancedAnalysis(detail.segment_score_id, {
        force_refresh: forceRefresh,
        allow_web_search: true,
        include_memory: true,
      });
      setEnhancement(result);
      if (result.status === "ready") {
        message.success(forceRefresh ? "分段增强分析已重新生成。" : "分段增强分析已准备完成。");
      } else if (result.status === "failed") {
        message.warning(result.failure_reason || "分段增强分析生成失败，请稍后重试。");
      }
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setEnhancementLoading(false);
    }
  };

  return (
    <Drawer
      title={detail ? `分段分析详情 · ${detail.title}` : "分段分析详情"}
      open={open}
      onClose={onClose}
      width={720}
    >
      {loading ? (
        <Space direction="vertical" style={{ width: "100%" }} size={18}>
          <Skeleton.Button active block size="large" />
          <Skeleton active paragraph={{ rows: 10 }} />
        </Space>
      ) : !detail ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="选择一个分段后查看详细证据。" />
      ) : (
        <Space direction="vertical" style={{ width: "100%" }} size={18}>
          <Alert type="warning" showIcon message="一句话解释" description={formatErrorText(detail.overall_explanation)} />

          {detail.generated_at ? (
            <Typography.Text type="secondary">分析生成时间：{detail.generated_at}</Typography.Text>
          ) : null}

          <div className="glance-strip">
            <div className="glance-card">
              <Typography.Text type="secondary">困惑得分</Typography.Text>
              <Typography.Title level={3}>{detail.confusion_score}</Typography.Title>
              <Typography.Text type="secondary">0-100 的规则评分</Typography.Text>
            </div>
            <div className="glance-card">
              <Typography.Text type="secondary">风险等级</Typography.Text>
              <div style={{ margin: "8px 0 10px" }}>
                <RiskLevelTag riskLevel={detail.risk_level} />
              </div>
              <Typography.Text type="secondary">用于快速判断是否优先复盘</Typography.Text>
            </div>
            <div className="glance-card">
              <Typography.Text type="secondary">数据完整度</Typography.Text>
              <Typography.Title level={3}>{(detail.data_coverage_percent ?? 0)}%</Typography.Title>
              <Typography.Text type="secondary">{(detail.confidence_label ?? "未知可信度")}</Typography.Text>
            </div>
            <div className="glance-card">
              <Typography.Text type="secondary">首要拉高信号</Typography.Text>
              <Typography.Title level={4} style={{ marginBottom: 8 }}>
                {primarySignal ? primarySignal.label : "-"}
              </Typography.Title>
              <Typography.Text type="secondary">
                {primarySignal
                  ? `${primarySignal.value_percent}% · 有效贡献 ${primarySignal.contribution_score} 分`
                  : "当前没有明显主导信号"}
              </Typography.Text>
            </div>
            <div className="glance-card">
              <Typography.Text type="secondary">主要错误</Typography.Text>
              <Typography.Paragraph style={{ margin: "8px 0 0" }}>
                {formatErrorText(detail.main_error_summary)}
              </Typography.Paragraph>
            </div>
          </div>

          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="分段标题">{detail.title}</Descriptions.Item>
            <Descriptions.Item label="知识点">{detail.knowledge_point_name || "-"}</Descriptions.Item>
            <Descriptions.Item label="时间区间">
              {detail.start_minute} - {detail.end_minute} 分钟
            </Descriptions.Item>
            <Descriptions.Item label="风险等级">
              <RiskLevelTag riskLevel={detail.risk_level} />
            </Descriptions.Item>
            <Descriptions.Item label="困惑得分">{detail.confusion_score}</Descriptions.Item>
            <Descriptions.Item label="数据完整度">
              {(detail.data_coverage_percent ?? 0)}% · {(detail.confidence_label ?? "未知可信度")}
            </Descriptions.Item>
            <Descriptions.Item label="评分公式">{detail.score_formula}</Descriptions.Item>
            <Descriptions.Item label="主要错误">{formatErrorText(detail.main_error_summary)}</Descriptions.Item>
            <Descriptions.Item label="教师备注">{detail.teacher_notes || "-"}</Descriptions.Item>
          </Descriptions>

          <section className="suggestion-card">
            <Space style={{ width: "100%", justifyContent: "space-between" }} align="start">
              <div>
                <Typography.Title level={5}>再教学闭环记录</Typography.Title>
                <Typography.Text type="secondary">
                  记录教师是否采用建议，并在后续课堂中核验同一知识点的变化。
                </Typography.Text>
                {intervention ? (
                  <>
                    <Typography.Paragraph style={{ marginTop: 8, marginBottom: 0 }}>
                      当前状态：{intervention.status}；记录时间：{intervention.created_at}
                    </Typography.Paragraph>
                    {intervention.outcome_summary ? (
                      <Typography.Paragraph style={{ marginTop: 4, marginBottom: 0 }}>
                        核验结果：{intervention.outcome_summary}
                      </Typography.Paragraph>
                    ) : null}
                  </>
                ) : null}
              </div>
              <Space wrap>
                <Button type="primary" loading={interventionLoading} onClick={() => void handleRecordIntervention()}>
                  {intervention ? "再次记录干预" : "标记已采纳建议"}
                </Button>
                {intervention ? (
                  <Button loading={interventionLoading} onClick={() => void handleVerifyIntervention()}>
                    自动核验后续课堂
                  </Button>
                ) : null}
              </Space>
            </Space>
          </section>

          <div>
            <Typography.Title level={5}>信号拆解</Typography.Title>
            <Table
              size="small"
              rowKey="key"
              pagination={false}
              dataSource={sortedSignals}
              locale={{ emptyText: "当前没有可展示的评分信号。" }}
              columns={[
                {
                  title: "信号",
                  dataIndex: "label",
                  render: (_, record) => (
                    <Space direction="vertical" size={2}>
                      <Typography.Text strong>{record.label}</Typography.Text>
                      <Typography.Text type="secondary">{record.description}</Typography.Text>
                    </Space>
                  ),
                },
                {
                  title: "信号值",
                  width: 100,
                  render: (_, record) => `${record.value_percent}%`,
                },
                {
                  title: "有效权重",
                  width: 100,
                  render: (_, record) => (record.is_available ? `${(record.effective_weight_percent ?? 0)}%` : "缺失"),
                },
                {
                  title: "样本量",
                  width: 90,
                  render: (_, record) => `${record.samples}`,
                },
                {
                  title: "贡献分",
                  width: 100,
                  render: (_, record) => `${record.contribution_score}`,
                },
              ]}
            />
          </div>

          <div>
            <Typography.Title level={5}>信号可视化</Typography.Title>
            <Space direction="vertical" style={{ width: "100%" }}>
              {sortedSignals.map((item) => (
                <div key={item.key}>
                  <Space style={{ width: "100%", justifyContent: "space-between" }}>
                    <Typography.Text strong>{item.label}</Typography.Text>
                    <Typography.Text>
                      {item.is_available ? `${item.value_percent}% · 有效贡献 ${item.contribution_score} 分` : "数据缺失"}
                    </Typography.Text>
                  </Space>
                  <Progress percent={item.is_available ? item.value_percent : 0} showInfo={false} strokeColor="#d94841" />
                  <Typography.Text type="secondary" className="signal-evidence">
                    {item.evidence_summary}
                  </Typography.Text>
                </div>
              ))}
            </Space>
          </div>

          <div>
            <Typography.Title level={5}>典型错误统计</Typography.Title>
            <Table
              size="small"
              rowKey="label"
              pagination={false}
              locale={{ emptyText: "该分段没有聚集性的错误类型。" }}
              dataSource={detail.error_summary}
              columns={[
                { title: "错误类型", dataIndex: "label", render: (value: string) => formatErrorLabel(value) },
                { title: "出现次数", dataIndex: "count", width: 120 },
              ]}
            />
          </div>

          <div>
            <Space style={{ width: "100%", justifyContent: "space-between" }}>
              <div>
                <Typography.Title level={5}>增强解释</Typography.Title>
                <Typography.Text type="secondary">
                  这一层不会改写规则分数，而是把讲稿、PPT 和高风险证据整理成更容易讲清的解释。
                </Typography.Text>
              </div>
              <Space>
                <Button
                  type="primary"
                  loading={enhancementLoading}
                  onClick={() => void handleGenerateEnhancement(false)}
                >
                  {enhancement ? "刷新增强分析" : "生成增强分析"}
                </Button>
                <Button loading={enhancementLoading} onClick={() => void handleGenerateEnhancement(true)}>
                  重新生成
                </Button>
              </Space>
            </Space>

            {enhancementLoading ? <Spin style={{ marginTop: 12 }} /> : null}

            {!enhancement ? (
              <Empty
                style={{ marginTop: 12 }}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="当前还没有这个分段的增强解释。"
              />
            ) : enhancement.status === "failed" ? (
              <Alert
                style={{ marginTop: 12 }}
                type="error"
                showIcon
                message="增强解释生成失败"
                description={enhancement.failure_reason || "请稍后重试。"}
              />
            ) : enhancement.status === "ready" ? (
              <Space direction="vertical" style={{ width: "100%", marginTop: 12 }} size={14}>
                <Tag>{enhancement.generation_mode_label}</Tag>
                <section className="suggestion-card">
                  <Typography.Title level={5}>诊断</Typography.Title>
                  <Typography.Paragraph className="suggestion-content">
                    {enhancement.diagnosis}
                  </Typography.Paragraph>
                </section>

                <section className="suggestion-card">
                  <Typography.Title level={5}>证据叙事</Typography.Title>
                  <Typography.Paragraph className="suggestion-content">
                    {enhancement.evidence_story}
                  </Typography.Paragraph>
                </section>

                <div className="enhanced-grid">
                  <section className="suggestion-card">
                    <Typography.Title level={5}>教师关注重点</Typography.Title>
                    <ul className="suggestion-list">
                      {enhancement.teacher_focus.map((item, index) => (
                        <li key={`${item}-${index}`}>{item}</li>
                      ))}
                    </ul>
                  </section>

                  <section className="suggestion-card">
                    <Typography.Title level={5}>推荐复核项</Typography.Title>
                    <ul className="suggestion-list">
                      {enhancement.recommended_checks.map((item, index) => (
                        <li key={`${item}-${index}`}>{item}</li>
                      ))}
                    </ul>
                  </section>
                </div>

                <section className="suggestion-card">
                  <Typography.Title level={5}>课堂内记忆</Typography.Title>
                  {enhancement.memory_notes.length === 0 ? (
                    <Typography.Text type="secondary">当前还没有可复用的课堂内记忆。</Typography.Text>
                  ) : (
                    <ul className="suggestion-list">
                      {enhancement.memory_notes.map((item, index) => (
                        <li key={`${item}-${index}`}>{item}</li>
                      ))}
                    </ul>
                  )}
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
              <Typography.Text type="secondary">增强分析仍在生成中，请稍后刷新。</Typography.Text>
            )}
          </div>
        </Space>
      )}
    </Drawer>
  );
}
