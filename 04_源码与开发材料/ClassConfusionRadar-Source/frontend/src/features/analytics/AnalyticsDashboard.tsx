/**
 * 本文件的作用是：实现 AnalyticsDashboard 对应的前端交互与界面展示。
 */
import { Alert, Button, Empty, Space, Table, Tag, Typography } from "antd";
import ReactECharts from "echarts-for-react";
import { RiskLevelTag } from "../../components/StatusTag";
import type { AnalyticsOverview } from "../../types/api";
import { formatErrorLabel, formatErrorText } from "../../utils/labels";
import { EnhancedSessionAnalysisPanel } from "./EnhancedSessionAnalysisPanel";

interface AnalyticsDashboardProps {
  sessionId: number;
  overview: AnalyticsOverview;
  onInspectSegment: (segmentId: number) => void;
  onOpenSuggestions?: () => void;
}

export function AnalyticsDashboard({
  sessionId,
  overview,
  onInspectSegment,
  onOpenSuggestions,
}: AnalyticsDashboardProps) {
  if (!overview.has_analysis) {
    return (
      <Empty
        description={
          <Space direction="vertical" size={4}>
            <Typography.Text>当前课堂尚未运行分析，请先完成数据上传与教学分段，再执行困惑分析。</Typography.Text>
            <Typography.Text type="secondary">运行分析后，这里会展示热力图、错误统计和高风险分段排名。</Typography.Text>
          </Space>
        }
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  const segmentItems = Array.from(
    new Map(
      overview.heatmap_cells.map((cell) => [
        cell.segment_id,
        { segment_id: cell.segment_id, title: cell.segment_title },
      ]),
    ).values(),
  );
  const segmentTitles = segmentItems.map((item) => item.title);
  const segmentIndexById = new Map(segmentItems.map((item, index) => [item.segment_id, index]));
  const signalLabels = overview.scoring_rules.map((item) => item.label);
  const signalIndexByKey = new Map(overview.scoring_rules.map((item, index) => [item.key, index]));

  // 同一分段、同一指标只保留一个格子。即使后端历史数据里出现重复记录，
  // 也不会在同一个位置重复绘制数字。
  const heatmapCellMap = new Map<string, [number, number, number]>();
  overview.heatmap_cells.forEach((cell) => {
    const x = segmentIndexById.get(cell.segment_id);
    const y = signalIndexByKey.get(cell.signal_key);
    if (x === undefined || y === undefined) {
      return;
    }
    heatmapCellMap.set(`${cell.segment_id}:${cell.signal_key}`, [x, y, cell.value]);
  });
  const heatmapData = Array.from(heatmapCellMap.values());
  const topRiskSegment = overview.high_risk_segments[0] ?? null;
  const analyzedSegments = Array.from(
    new Map(
      overview.heatmap_cells.map((cell) => [cell.segment_id, { segment_id: cell.segment_id, title: cell.segment_title }]),
    ).values(),
  );

  return (
    <Space direction="vertical" style={{ width: "100%" }} size={18}>
      <EnhancedSessionAnalysisPanel
        sessionId={sessionId}
        hasAnalysis={overview.has_analysis}
        onInspectSegment={onInspectSegment}
      />

      <Alert
        type="info"
        showIcon
        message="评分规则一眼看懂"
        description={
          <Space direction="vertical" size={8}>
            <Typography.Text>{overview.score_formula}</Typography.Text>
            <Space wrap>
              {overview.scoring_rules.map((rule) => (
                <Tag key={rule.key} color="default">
                  {rule.label} 基础权重 {rule.weight_percent}%
                </Tag>
              ))}
              <Tag color="blue">平均数据完整度 {(overview.summary.average_data_coverage_percent ?? 0)}%</Tag>
              <Tag color={((overview.summary.low_confidence_count ?? 0) ?? 0) > 0 ? "orange" : "green"}>
                低可信分段 {(overview.summary.low_confidence_count ?? 0)} 个
              </Tag>
            </Space>
          </Space>
        }
      />

      {topRiskSegment ? (
        <div className="risk-spotlight">
          <div>
            <Typography.Text className="eyebrow-text">本次最值得讲解的分段</Typography.Text>
            <Typography.Title level={3}>{topRiskSegment.title}</Typography.Title>
            <Typography.Paragraph>{formatErrorText(topRiskSegment.overall_explanation)}</Typography.Paragraph>
            <Space wrap>
              <RiskLevelTag riskLevel={topRiskSegment.risk_level} />
              {topRiskSegment.knowledge_point_name ? <Tag color="gold">{topRiskSegment.knowledge_point_name}</Tag> : null}
              {topRiskSegment.primary_signal_label ? (
                <Tag color="volcano">
                  主因：{topRiskSegment.primary_signal_label} {topRiskSegment.primary_signal_value_percent}%
                </Tag>
              ) : null}
              <Tag color={topRiskSegment.confidence_level === "low" ? "orange" : "blue"}>
                数据完整度 {(topRiskSegment.data_coverage_percent ?? 0)}% · {(topRiskSegment.confidence_label ?? "未知可信度")}
              </Tag>
            </Space>
            <div className="hero-actions">
              <Button type="primary" onClick={() => onInspectSegment(topRiskSegment.segment_id)}>
                先看这个分段
              </Button>
              {onOpenSuggestions ? (
                <Button onClick={onOpenSuggestions}>再去教学建议</Button>
              ) : null}
            </div>
          </div>
          <div className="spotlight-score-card">
            <Typography.Text type="secondary">困惑得分</Typography.Text>
            <Typography.Title level={1}>{topRiskSegment.confusion_score}</Typography.Title>
            <Typography.Text type="secondary">高风险分段应优先复盘、重讲和追问。</Typography.Text>
          </div>
        </div>
      ) : (
        <Alert
          type="success"
          showIcon
          message="本次没有识别到高风险分段"
          description="可以继续展示热力图和分段详情，说明系统已完成分析，但当前课堂整体风险较低。"
        />
      )}

      <div className="analytics-summary-strip">
        <div className="glance-card">
          <Typography.Text type="secondary">平均困惑得分</Typography.Text>
          <Typography.Title level={3}>{overview.summary.average_score}</Typography.Title>
          <Typography.Text type="secondary">本次分析全部分段的平均值</Typography.Text>
        </div>
        <div className="glance-card">
          <Typography.Text type="secondary">已分析分段</Typography.Text>
          <Typography.Title level={3}>{overview.summary.total_segments}</Typography.Title>
          <Typography.Text type="secondary">当前课堂已经生成结果的分段数</Typography.Text>
        </div>
        <div className="glance-card">
          <Typography.Text type="secondary">高风险分段</Typography.Text>
          <Typography.Title level={3}>{overview.summary.high_risk_count}</Typography.Title>
          <Typography.Text type="secondary">建议优先复盘并生成教学建议</Typography.Text>
        </div>
        <div className="glance-card">
          <Typography.Text type="secondary">极高风险分段</Typography.Text>
          <Typography.Title level={3}>{overview.summary.critical_count}</Typography.Title>
          <Typography.Text type="secondary">最值得优先复盘</Typography.Text>
        </div>
        <div className="glance-card">
          <Typography.Text type="secondary">平均数据完整度</Typography.Text>
          <Typography.Title level={3}>{(overview.summary.average_data_coverage_percent ?? 0)}%</Typography.Title>
          <Typography.Text type="secondary">用于区分风险程度与证据可信度</Typography.Text>
        </div>
      </div>

      <div className="overview-grid">
        <div className="analytics-panel">
          <div className="panel-header">
            <div>
              <Typography.Title level={5}>困惑热力图</Typography.Title>
              <Typography.Text type="secondary">横轴是教学分段，纵轴是四个评分信号，颜色越深表示风险越高。</Typography.Text>
            </div>
          </div>
          <ReactECharts
            option={{
              animation: false,
              tooltip: {
                formatter: (params: { value?: [number, number, number] }) => {
                  const value = params.value ?? [0, 0, 0];
                  const segment = segmentTitles[value[0]] ?? "未知分段";
                  const signal = signalLabels[value[1]] ?? "未知信号";
                  return `${segment}<br/>${signal}：<strong>${Number(value[2]).toFixed(2)}</strong>`;
                },
              },
              grid: { left: 108, right: 28, top: 26, bottom: 88, containLabel: false },
              xAxis: {
                type: "category",
                data: segmentTitles,
                axisTick: { alignWithLabel: true },
                axisLabel: {
                  interval: 0,
                  rotate: segmentTitles.length > 5 ? 28 : 18,
                  margin: 14,
                  formatter: (value: string) => value.length > 9 ? `${value.slice(0, 9)}…` : value,
                },
              },
              yAxis: {
                type: "category",
                data: signalLabels,
                axisLabel: { margin: 16 },
              },
              visualMap: {
                min: 0,
                max: 100,
                orient: "horizontal",
                left: "center",
                bottom: 6,
                calculable: false,
                inRange: { color: ["#f2efe4", "#f5c98e", "#ee7b52", "#cf1322"] },
              },
              series: [{
                type: "heatmap",
                data: heatmapData,
                label: {
                  show: true,
                  fontSize: 13,
                  formatter: (params: { value?: [number, number, number] }) => {
                    const score = Number(params.value?.[2] ?? 0);
                    return Number.isInteger(score) ? String(score) : score.toFixed(1);
                  },
                },
                labelLayout: { hideOverlap: true },
                progressive: 0,
                emphasis: {
                  itemStyle: { shadowBlur: 8, shadowColor: "rgba(0,0,0,0.18)" },
                },
              }],
            }}
            style={{ height: 410 }}
          />
        </div>
        <div className="analytics-panel">
          <div className="panel-header">
            <div>
              <Typography.Title level={5}>主要错误类型</Typography.Title>
              <Typography.Text type="secondary">用来说明学生困惑主要集中在什么类型的代码错误或执行问题。</Typography.Text>
            </div>
          </div>
          {overview.top_errors.length === 0 ? (
            <Empty description="当前分析结果没有聚集性的提交错误。" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <ReactECharts
              option={{
                tooltip: { trigger: "axis" },
                grid: { left: 48, right: 20, top: 24, bottom: 86, containLabel: true },
                xAxis: {
                  type: "category",
                  data: overview.top_errors.map((item) => formatErrorLabel(item.label)),
                  axisLabel: {
                    interval: 0,
                    rotate: 18,
                    margin: 14,
                    formatter: (value: string) => value.length > 7 ? `${value.slice(0, 7)}…` : value,
                  },
                },
                yAxis: { type: "value" },
                series: [
                  {
                    type: "bar",
                    data: overview.top_errors.map((item) => item.count),
                    itemStyle: { color: "#d94841", borderRadius: [8, 8, 0, 0] },
                  },
                ],
              }}
              style={{ height: 380 }}
            />
          )}
        </div>
      </div>

      <div>
        <Typography.Title level={5}>高风险分段</Typography.Title>
        {overview.high_risk_segments.length === 0 ? (
          <Empty
            description="本次分析没有识别到高风险分段，你仍然可以查看任意已分析分段的详细信号。"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <Table
            rowKey="segment_score_id"
            pagination={false}
            size="middle"
            dataSource={overview.high_risk_segments}
            rowClassName={(record, index) => (index === 0 ? "table-row-spotlight" : "")}
            columns={[
              { title: "分段标题", dataIndex: "title" },
              { title: "知识点", dataIndex: "knowledge_point_name", render: (value) => value || "-" },
              {
                title: "困惑得分",
                dataIndex: "confusion_score",
                width: 100,
              },
              {
                title: "风险等级",
                dataIndex: "risk_level",
                width: 100,
                render: (value) => <RiskLevelTag riskLevel={value} />,
              },
              {
                title: "可信度",
                width: 120,
                render: (_, record) => `${(record.data_coverage_percent ?? 0)}% · ${(record.confidence_label ?? "未知可信度")}`,
              },
              {
                title: "主要原因",
                render: (_, record) =>
                  record.primary_signal_label ? (
                    <Typography.Text>
                      {record.primary_signal_label} {record.primary_signal_value_percent}% ，贡献{" "}
                      {record.primary_signal_contribution_score} 分
                    </Typography.Text>
                  ) : (
                    "-"
                  ),
              },
              {
                title: "主要错误",
                dataIndex: "main_error_summary",
                render: (value: string) => <Typography.Text type="secondary">{formatErrorText(value)}</Typography.Text>,
              },
              {
                title: "一句话解释",
                dataIndex: "overall_explanation",
                render: (value: string) => (
                  <Typography.Paragraph
                    style={{ marginBottom: 0 }}
                    ellipsis={{ rows: 2, expandable: true, symbol: "展开" }}
                  >
                    {formatErrorText(value)}
                  </Typography.Paragraph>
                ),
              },
              {
                title: "操作",
                width: 120,
                render: (_, record) => (
                  <Button type="link" onClick={() => onInspectSegment(record.segment_id)}>
                    查看详情
                  </Button>
                ),
              },
            ]}
          />
        )}
      </div>

      <div>
        <Typography.Title level={5}>全部已分析分段</Typography.Title>
        <Table
          rowKey="segment_id"
          pagination={false}
          dataSource={analyzedSegments}
          columns={[
            { title: "分段标题", dataIndex: "title" },
            {
              title: "操作",
              width: 140,
              render: (_, record) => (
                <Button type="link" onClick={() => onInspectSegment(record.segment_id)}>
                  查看分段详情
                </Button>
              ),
            },
          ]}
        />
      </div>
    </Space>
  );
}
