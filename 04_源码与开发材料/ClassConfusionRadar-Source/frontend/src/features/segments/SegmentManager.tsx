/**
 * 本文件的作用是：实现 SegmentManager 对应的前端交互与界面展示。
 */
import { useEffect, useMemo, useState } from "react";
import { Alert, App, Button, Form, Input, InputNumber, Modal, Select, Space, Table, Typography } from "antd";
import {
  createKnowledgePoint,
  deleteKnowledgePoint,
  updateKnowledgePoint,
} from "../../api/knowledgePoints";
import { autoBuildSegments, createSegment, deleteSegment, updateSegment } from "../../api/segments";
import type { FileKind, KnowledgePointItem, SessionDetail, TeachingSegmentItem } from "../../types/api";
import { formatFileKind } from "../../utils/labels";

interface SegmentManagerProps {
  session: SessionDetail;
  onRefresh: () => Promise<void>;
}

interface KnowledgePointFormValues {
  name: string;
  topic_area?: string;
  description?: string;
  display_order: number;
}

interface SegmentFormValues {
  title: string;
  knowledge_point_id?: number | null;
  start_minute: number;
  end_minute: number;
  display_order: number;
  teacher_notes?: string;
}

export function SegmentManager({ session, onRefresh }: SegmentManagerProps) {
  const { message, modal } = App.useApp();
  const [knowledgeCreateForm] = Form.useForm<KnowledgePointFormValues>();
  const [knowledgeEditForm] = Form.useForm<KnowledgePointFormValues>();
  const [segmentCreateForm] = Form.useForm<SegmentFormValues>();
  const [segmentEditForm] = Form.useForm<SegmentFormValues>();
  const [editingSegment, setEditingSegment] = useState<TeachingSegmentItem | null>(null);
  const [editingKnowledgePoint, setEditingKnowledgePoint] = useState<KnowledgePointItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [autoBuilding, setAutoBuilding] = useState(false);
  const [deletingKnowledgePointId, setDeletingKnowledgePointId] = useState<number | null>(null);
  const [deletingSegmentId, setDeletingSegmentId] = useState<number | null>(null);

  const successfulFileKinds = useMemo(
    () => new Set(session.uploaded_files.filter((item) => item.parse_status === "success").map((item) => item.file_kind)),
    [session.uploaded_files],
  );
  const missingAutoBuildKinds = useMemo(
    () =>
      (["transcript", "ppt_timeline"] satisfies FileKind[]).filter((fileKind) => !successfulFileKinds.has(fileKind)),
    [successfulFileKinds],
  );
  const canAutoBuild = missingAutoBuildKinds.length === 0;

  const knowledgeOptions = useMemo(
    () =>
      session.knowledge_points.map((item) => ({
        label: `${item.display_order}. ${item.name}`,
        value: item.id,
      })),
    [session.knowledge_points],
  );

  useEffect(() => {
    knowledgeCreateForm.setFieldsValue({
      display_order: session.knowledge_points.length + 1,
    });
    segmentCreateForm.setFieldsValue({
      display_order: session.segments.length + 1,
    });
  }, [knowledgeCreateForm, segmentCreateForm, session.knowledge_points.length, session.segments.length]);

  const openKnowledgePointEditor = (knowledgePoint: KnowledgePointItem) => {
    setEditingKnowledgePoint(knowledgePoint);
    knowledgeEditForm.setFieldsValue({
      name: knowledgePoint.name,
      topic_area: knowledgePoint.topic_area ?? undefined,
      description: knowledgePoint.description ?? undefined,
      display_order: knowledgePoint.display_order,
    });
  };

  const openSegmentEditor = (segment: TeachingSegmentItem) => {
    setEditingSegment(segment);
    segmentEditForm.setFieldsValue({
      title: segment.title,
      knowledge_point_id: segment.knowledge_point_id,
      start_minute: segment.start_minute,
      end_minute: segment.end_minute,
      display_order: segment.display_order,
      teacher_notes: segment.teacher_notes ?? undefined,
    });
  };

  const runAutoBuild = async (replaceExisting: boolean) => {
    try {
      setAutoBuilding(true);
      const result = await autoBuildSegments(session.id, { replace_existing: replaceExisting });
      message.success(result.message);
      await onRefresh();
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setAutoBuilding(false);
    }
  };

  const handleAutoBuild = async () => {
    if (!canAutoBuild) {
      message.warning(`自动生成前，请先上传：${missingAutoBuildKinds.map(formatFileKind).join("、")}。`);
      return;
    }

    if (session.segments.length === 0) {
      await runAutoBuild(false);
      return;
    }

    modal.confirm({
      title: "替换现有教学分段",
      content: "自动生成会先删除当前分段，再根据 transcript 和 PPT 时间轴重新生成。你仍然可以在生成后继续手动编辑。",
      okText: "确认替换并生成",
      cancelText: "取消",
      onOk: async () => {
        await runAutoBuild(true);
      },
    });
  };

  const handleCreateKnowledgePoint = async (values: KnowledgePointFormValues) => {
    try {
      setSubmitting(true);
      await createKnowledgePoint(session.id, values);
      knowledgeCreateForm.resetFields();
      message.success("知识点已新增。");
      await onRefresh();
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateKnowledgePoint = async () => {
    if (!editingKnowledgePoint) {
      return;
    }

    try {
      const values = await knowledgeEditForm.validateFields();
      setSubmitting(true);
      await updateKnowledgePoint(editingKnowledgePoint.id, values);
      setEditingKnowledgePoint(null);
      message.success("知识点已更新。");
      await onRefresh();
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteKnowledgePoint = async (knowledgePointId: number) => {
    try {
      setDeletingKnowledgePointId(knowledgePointId);
      await deleteKnowledgePoint(knowledgePointId);
      message.success("知识点已删除。");
      await onRefresh();
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setDeletingKnowledgePointId(null);
    }
  };

  const handleCreateSegment = async (values: SegmentFormValues) => {
    try {
      setSubmitting(true);
      await createSegment(session.id, values);
      segmentCreateForm.resetFields();
      message.success("教学分段已新增。");
      await onRefresh();
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateSegment = async () => {
    if (!editingSegment) {
      return;
    }

    try {
      const values = await segmentEditForm.validateFields();
      setSubmitting(true);
      await updateSegment(editingSegment.id, values);
      setEditingSegment(null);
      message.success("教学分段已更新。");
      await onRefresh();
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteSegment = async (segmentId: number) => {
    try {
      setDeletingSegmentId(segmentId);
      await deleteSegment(segmentId);
      message.success("教学分段已删除。");
      await onRefresh();
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setDeletingSegmentId(null);
    }
  };

  return (
    <div className="segment-layout">
      <div className="page-stack">
        <Typography.Title level={5}>知识点管理</Typography.Title>
        <Form layout="vertical" form={knowledgeCreateForm} onFinish={handleCreateKnowledgePoint}>
          <Form.Item
            label="知识点名称"
            name="name"
            rules={[{ required: true, message: "请输入知识点名称" }]}
          >
            <Input placeholder="例如：条件判断 / 链表遍历 / while 循环" />
          </Form.Item>
          <Form.Item label="所属主题" name="topic_area">
            <Input placeholder="例如：控制流 / Python 基础 / 数据结构" />
          </Form.Item>
          <Form.Item
            label="显示顺序"
            name="display_order"
            rules={[{ required: true, message: "请输入顺序" }]}
          >
            <InputNumber min={1} max={99} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="说明" name="description">
            <Input.TextArea rows={3} placeholder="记录该知识点的教学目标、易错点或备注" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting}>
            添加知识点
          </Button>
        </Form>

        <Table<KnowledgePointItem>
          rowKey="id"
          pagination={false}
          locale={{ emptyText: "当前还没有知识点，请先新增。" }}
          dataSource={session.knowledge_points}
          columns={[
            { title: "顺序", dataIndex: "display_order", width: 80 },
            { title: "名称", dataIndex: "name" },
            { title: "主题", dataIndex: "topic_area", render: (value) => value || "-" },
            {
              title: "操作",
              render: (_, record) => (
                <Space>
                  <Button type="link" onClick={() => openKnowledgePointEditor(record)}>
                    编辑
                  </Button>
                  <Button
                    type="link"
                    danger
                    loading={deletingKnowledgePointId === record.id}
                    onClick={() => handleDeleteKnowledgePoint(record.id)}
                  >
                    删除
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </div>

      <div className="page-stack">
        <div>
          <Space align="center" style={{ justifyContent: "space-between", width: "100%" }}>
            <Typography.Title level={5} style={{ marginBottom: 0 }}>
              教学分段构建
            </Typography.Title>
            <Button type="primary" loading={autoBuilding} onClick={handleAutoBuild}>
              自动生成分段
            </Button>
          </Space>
          <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
            自动生成会读取已上传的课堂讲稿和 PPT 时间轴，按 PPT 时间窗对齐 transcript 内容后创建候选分段。
          </Typography.Paragraph>
        </div>

        {canAutoBuild ? (
          <Alert
            type="success"
            showIcon
            message="已满足自动分段条件"
            description="你可以直接点击“自动生成分段”，然后再逐条检查、编辑或删除结果。"
          />
        ) : (
          <Alert
            type="info"
            showIcon
            message="自动分段前还需要上传材料"
            description={`缺少：${missingAutoBuildKinds.map(formatFileKind).join("、")}。`}
          />
        )}

        <Form layout="vertical" form={segmentCreateForm} onFinish={handleCreateSegment}>
          <div className="form-grid">
            <Form.Item
              label="分段标题"
              name="title"
              rules={[{ required: true, message: "请输入分段标题" }]}
            >
              <Input placeholder="例如：for 循环执行流程讲解" />
            </Form.Item>
            <Form.Item label="关联知识点" name="knowledge_point_id">
              <Select allowClear options={knowledgeOptions} placeholder="可选，便于分析归因" />
            </Form.Item>
            <Form.Item
              label="开始分钟"
              name="start_minute"
              rules={[{ required: true, message: "请输入开始时间" }]}
            >
              <InputNumber min={0} max={session.duration_minutes} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="结束分钟"
              name="end_minute"
              rules={[{ required: true, message: "请输入结束时间" }]}
            >
              <InputNumber min={0} max={session.duration_minutes} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="显示顺序"
              name="display_order"
              rules={[{ required: true, message: "请输入显示顺序" }]}
            >
              <InputNumber min={1} max={99} style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <Form.Item label="教师备注" name="teacher_notes">
            <Input.TextArea rows={3} placeholder="记录这段教学的预期目标、课堂现象或需要重点解释的点" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting}>
            添加教学分段
          </Button>
        </Form>

        <Table<TeachingSegmentItem>
          rowKey="id"
          pagination={false}
          locale={{ emptyText: "当前还没有教学分段，请先新增或自动生成。" }}
          dataSource={session.segments}
          columns={[
            { title: "顺序", dataIndex: "display_order", width: 70 },
            { title: "分段标题", dataIndex: "title" },
            {
              title: "知识点",
              dataIndex: "knowledge_point_id",
              render: (knowledgePointId: number | null) =>
                session.knowledge_points.find((item) => item.id === knowledgePointId)?.name || "-",
            },
            {
              title: "时间区间",
              render: (_, record) => `${record.start_minute} - ${record.end_minute} 分钟`,
            },
            {
              title: "操作",
              render: (_, record) => (
                <Space>
                  <Button type="link" onClick={() => openSegmentEditor(record)}>
                    编辑
                  </Button>
                  <Button
                    type="link"
                    danger
                    loading={deletingSegmentId === record.id}
                    onClick={() => handleDeleteSegment(record.id)}
                  >
                    删除
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </div>

      <Modal
        title="编辑知识点"
        open={Boolean(editingKnowledgePoint)}
        onCancel={() => setEditingKnowledgePoint(null)}
        onOk={handleUpdateKnowledgePoint}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={knowledgeEditForm} layout="vertical">
          <Form.Item
            label="知识点名称"
            name="name"
            rules={[{ required: true, message: "请输入知识点名称" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="所属主题" name="topic_area">
            <Input />
          </Form.Item>
          <Form.Item
            label="显示顺序"
            name="display_order"
            rules={[{ required: true, message: "请输入显示顺序" }]}
          >
            <InputNumber min={1} max={99} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="编辑教学分段"
        open={Boolean(editingSegment)}
        onCancel={() => setEditingSegment(null)}
        onOk={handleUpdateSegment}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={segmentEditForm} layout="vertical">
          <Form.Item
            label="分段标题"
            name="title"
            rules={[{ required: true, message: "请输入分段标题" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="关联知识点" name="knowledge_point_id">
            <Select allowClear options={knowledgeOptions} />
          </Form.Item>
          <div className="form-grid">
            <Form.Item
              label="开始分钟"
              name="start_minute"
              rules={[{ required: true, message: "请输入开始时间" }]}
            >
              <InputNumber min={0} max={session.duration_minutes} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="结束分钟"
              name="end_minute"
              rules={[{ required: true, message: "请输入结束时间" }]}
            >
              <InputNumber min={0} max={session.duration_minutes} style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <Form.Item
            label="显示顺序"
            name="display_order"
            rules={[{ required: true, message: "请输入显示顺序" }]}
          >
            <InputNumber min={1} max={99} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="教师备注" name="teacher_notes">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
