/**
 * 本文件的作用是：实现 SessionList 对应的前端交互与界面展示。
 */
import { Button, Empty, Space, Table, Tag, Typography } from "antd";
import { Link } from "react-router-dom";
import { SessionStatusTag } from "../../components/StatusTag";
import type { SessionSummary } from "../../types/api";
import { formatCourseType } from "../../utils/labels";

interface SessionListProps {
  sessions: SessionSummary[];
  loading: boolean;
  onDelete: (sessionId: number) => void;
}

export function SessionList({ sessions, loading, onDelete }: SessionListProps) {
  const getNextActionText = (session: SessionSummary) => {
    if (session.upload_count === 0) {
      return "先上传课堂数据";
    }
    if (session.segment_count === 0) {
      return "先构建教学分段";
    }
    if (session.status !== "analyzed") {
      return "运行困惑分析";
    }
    if (session.high_risk_count > 0) {
      return "进入教学建议页";
    }
    return "查看分段详情信号";
  };

  if (!loading && sessions.length === 0) {
    return (
      <Empty
        description={
          <Space direction="vertical" size={4}>
            <Typography.Text>还没有课堂场次，请先创建一场课堂。</Typography.Text>
          </Space>
        }
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      >
        <Button type="primary">
          <Link to="/sessions/new">创建第一场课堂</Link>
        </Button>
      </Empty>
    );
  }

  return (
    <Table
      rowKey="id"
      loading={loading}
      dataSource={sessions}
      size="middle"
      pagination={false}
      rowClassName={(record) => {
        if (record.high_risk_count > 0) {
          return "table-row-spotlight";
        }
        if (record.status === "analyzed") {
          return "table-row-complete";
        }
        return "";
      }}
      locale={{
        emptyText: "当前没有可展示的课堂场次。",
      }}
      columns={[
        {
          title: "课堂场次",
          dataIndex: "title",
          render: (_, record) => (
            <Space direction="vertical" size={3}>
              <Typography.Text strong>{record.title}</Typography.Text>
              <Typography.Text type="secondary">
                {formatCourseType(record.course_type)} · {record.class_date}
              </Typography.Text>
              {record.notes ? <Typography.Text type="secondary">{record.notes}</Typography.Text> : null}
            </Space>
          ),
        },
        {
          title: "状态",
          render: (_, record) => (
            <Space wrap>
              <SessionStatusTag status={record.status} />
              {record.high_risk_count > 0 ? <Tag color="volcano">高风险 {record.high_risk_count}</Tag> : null}
            </Space>
          ),
        },
        {
          title: "准备度",
          render: (_, record) => (
            <Space direction="vertical" size={2}>
              <Typography.Text>上传文件 {record.upload_count}</Typography.Text>
              <Typography.Text type="secondary">教学分段 {record.segment_count}</Typography.Text>
            </Space>
          ),
        },
        {
          title: "下一步",
          render: (_, record) => (
            <Typography.Text type={record.high_risk_count > 0 ? undefined : "secondary"}>
              {getNextActionText(record)}
            </Typography.Text>
          ),
        },
        {
          title: "操作",
          key: "actions",
          render: (_, record) => (
            <Space>
              <Button type="link">
                <Link to={`/sessions/${record.id}`}>进入工作台</Link>
              </Button>
              <Button type="link" danger onClick={() => onDelete(record.id)}>
                删除
              </Button>
            </Space>
          ),
        },
      ]}
    />
  );
}
