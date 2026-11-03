/**
 * 本文件的作用是：实现 ApiIntegrationPanel 对应的前端交互与界面展示。
 */
import { Alert, Button, Empty, Space, Table, Tag, Typography } from "antd";
import type { AnalyticsOverview } from "../../types/api";
import { EnhancedSessionAnalysisPanel } from "./EnhancedSessionAnalysisPanel";

interface ApiIntegrationPanelProps {
  sessionId: number;
  overview: AnalyticsOverview;
  onInspectSegment: (segmentId: number) => void;
}

export function ApiIntegrationPanel({ sessionId, overview, onInspectSegment }: ApiIntegrationPanelProps) {
  const analyzedSegments = Array.from(
    new Map(
      overview.heatmap_cells.map((cell) => [
        cell.segment_id,
        {
          segment_id: cell.segment_id,
          title: cell.segment_title,
          isHighRisk: overview.high_risk_segments.some((item) => item.segment_id === cell.segment_id),
        },
      ]),
    ).values(),
  );

  return (
    <Space direction="vertical" style={{ width: "100%" }} size={18}>
      <Alert
        type="info"
        showIcon
        message="这页是做什么的？"
        description="这里把困惑分数、主要错误、讲稿和 PPT 证据整理成课堂结论。教师可以直接看‘哪里最需要重讲、为什么、接下来怎么处理’，不需要理解接口或技术术语。"
      />


      {!overview.has_analysis ? (
        <Alert
          type="warning"
          showIcon
          message="请先运行规则分析"
          description="增强解释依赖规则评分结果。先运行一次困惑分析，再回到这里查看课堂级和分段级解释。"
        />
      ) : (
        <>
          <EnhancedSessionAnalysisPanel
            sessionId={sessionId}
            hasAnalysis={overview.has_analysis}
            onInspectSegment={onInspectSegment}
          />

          <div className="analytics-panel">
            <div className="panel-header">
              <div>
                <Typography.Title level={5}>分段解释入口</Typography.Title>
                <Typography.Text type="secondary">
                  点击分段可打开详情抽屉，并继续查看讲稿、PPT 和高风险信号的组合解释。
                </Typography.Text>
              </div>
            </div>

            {analyzedSegments.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前还没有可展示的已分析分段。" />
            ) : (
              <Table
                rowKey="segment_id"
                pagination={false}
                dataSource={analyzedSegments}
                columns={[
                  {
                    title: "分段标题",
                    dataIndex: "title",
                    render: (value: string, record) => (
                      <Space>
                        <Typography.Text strong>{value}</Typography.Text>
                        {record.isHighRisk ? <Tag color="volcano">高风险优先</Tag> : <Tag>可查看增强解释</Tag>}
                      </Space>
                    ),
                  },
                  {
                    title: "操作",
                    width: 180,
                    render: (_, record) => (
                      <Button type="link" onClick={() => onInspectSegment(record.segment_id)}>
                        打开详情并分析
                      </Button>
                    ),
                  },
                ]}
              />
            )}
          </div>
        </>
      )}
    </Space>
  );
}
