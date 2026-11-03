/**
 * 本文件的作用是：实现 UploadPanel 对应的前端交互与界面展示。
 */
import { useMemo, useState } from "react";
import { Alert, App, Button, Modal, Select, Space, Table, Tag, Typography, Upload } from "antd";
import type { UploadFile } from "antd/es/upload/interface";
import { deleteUploadedFile, uploadSessionFile } from "../../api/files";
import { ParseStatusTag } from "../../components/StatusTag";
import type { FileKind, UploadedFileItem } from "../../types/api";
import { formatFileKind } from "../../utils/labels";
import {
  FIELD_SPECS,
  inferKindFromHeaders,
  normalizeRowsForUpload,
  parseTabularFile,
  suggestMappings,
  type ParsedTable,
} from "./tabularPreview";

interface UploadPanelProps {
  sessionId: number;
  files: UploadedFileItem[];
  onRefresh: () => Promise<void>;
}

const fileKindOptions = [
  { label: "课堂测验（quiz）", value: "quiz" },
  { label: "编程提交（submission）", value: "submission" },
  { label: "课堂互动（interaction）", value: "interaction" },
  { label: "课堂讲稿（transcript）", value: "transcript" },
  { label: "PPT 时间轴（ppt_timeline）", value: "ppt_timeline" },
] satisfies Array<{ label: string; value: FileKind }>;

const filenameKinds: Array<[string[], FileKind]> = [
  [["ppt_timeline", "ppt-time", "ppt时间轴", "ppt_时间轴"], "ppt_timeline"],
  [["submission", "编程提交", "提交"], "submission"],
  [["interaction", "课堂互动", "互动"], "interaction"],
  [["transcript", "课堂讲稿", "讲稿"], "transcript"],
  [["quiz", "课堂测验", "测验"], "quiz"],
];

function inferFileKind(filename: string): FileKind | null {
  const stem = filename.toLowerCase().replace(/\s+/g, "_");
  for (const [aliases, kind] of filenameKinds) {
    if (aliases.some((alias) => stem.includes(alias.toLowerCase()))) return kind;
  }
  return null;
}

export function UploadPanel({ sessionId, files, onRefresh }: UploadPanelProps) {
  const { message } = App.useApp();
  const [selectedKind, setSelectedKind] = useState<FileKind>("quiz");
  const [pendingFiles, setPendingFiles] = useState<UploadFile[]>([]);
  const [pendingFileName, setPendingFileName] = useState("");
  const [parsedTable, setParsedTable] = useState<ParsedTable | null>(null);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [mappingOpen, setMappingOpen] = useState(false);
  const [parsingFile, setParsingFile] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const refreshFiles = async () => {
    try {
      await onRefresh();
    } catch {
      message.warning("列表刷新失败，请稍后手动刷新页面。");
    }
  };

  const clearPending = () => {
    setPendingFiles([]);
    setPendingFileName("");
    setParsedTable(null);
    setColumnMapping({});
    setMappingOpen(false);
  };

  const applyKind = (kind: FileKind, table = parsedTable) => {
    setSelectedKind(kind);
    if (table) setColumnMapping(suggestMappings(kind, table.headers));
  };

  const uploadPreparedTable = async (
    originalName: string,
    kind: FileKind,
    table: ParsedTable,
    mapping: Record<string, string>,
    automatic = false,
  ) => {
    const requiredMissing = FIELD_SPECS[kind].filter((field) => field.required && !mapping[field.key]);
    if (requiredMissing.length) {
      throw new Error(`还有这些字段需要确认：${requiredMissing.map((item) => item.label).join("、")}`);
    }

    const normalizedCsv = normalizeRowsForUpload(kind, table, mapping);
    const originalStem = originalName.replace(/\.[^.]+$/, "") || kind;
    const normalizedFile = new File(
      [normalizedCsv],
      `${kind}_${originalStem}.csv`,
      { type: "text/csv;charset=utf-8" },
    );
    await uploadSessionFile(sessionId, kind, normalizedFile);
    clearPending();
    await refreshFiles();
    message.success(automatic ? "文件已自动识别、解析并上传完成。" : "文件已按确认后的列对应关系上传完成。");
  };

  const preparePendingFile = async (file: File & { uid?: string }) => {
    const actualFile = file as File;
    setPendingFileName(actualFile.name);
    setPendingFiles([{
      uid: file.uid ?? `${Date.now()}`,
      name: actualFile.name,
      size: actualFile.size,
      type: actualFile.type,
      status: "done",
      originFileObj: file as never,
    }]);
    setParsedTable(null);
    setColumnMapping({});

    try {
      setParsingFile(true);
      const table = await parseTabularFile(actualFile);
      if (!table.headers.length || !table.rows.length) throw new Error("没有读取到有效表头或数据行。");

      const byName = inferFileKind(actualFile.name);
      const byHeaders = inferKindFromHeaders(table.headers);
      const kind = byName ?? byHeaders ?? selectedKind;
      const mapping = suggestMappings(kind, table.headers);
      const requiredMissing = FIELD_SPECS[kind].filter((field) => field.required && !mapping[field.key]);

      setParsedTable(table);
      setSelectedKind(kind);
      setColumnMapping(mapping);
      setMappingOpen(true);

      if (requiredMissing.length === 0) {
        message.success(`已读取“${actualFile.name}”。确认列对应后会立即上传。`);
      } else if (byName || byHeaders) {
        message.info(`已识别为“${formatFileKind(kind)}”。请补充 ${requiredMissing.length} 个字段后确认上传。`);
      } else {
        message.info("已读取文件。请确认列对应关系，确认后会立即上传。 ");
      }
    } catch (error) {
      message.error((error as Error).message);
      setParsedTable(null);
    } finally {
      setParsingFile(false);
    }
  };

  const fields = FIELD_SPECS[selectedKind];
  const missingRequired = parsedTable
    ? fields.filter((field) => field.required && !columnMapping[field.key])
    : [];

  const handleConfirmUpload = async () => {
    if (!parsedTable) {
      message.warning("请重新选择文件。系统需要先读取表头。 ");
      return;
    }
    if (missingRequired.length) {
      message.warning(`请先为这些字段选择来源：${missingRequired.map((item) => item.label).join("、")}。`);
      return;
    }

    try {
      setUploading(true);
      await uploadPreparedTable(pendingFileName || `${selectedKind}.csv`, selectedKind, parsedTable, columnMapping);
    } catch (error) {
      await refreshFiles();
      message.error((error as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (fileId: number) => {
    try {
      setDeletingId(fileId);
      await deleteUploadedFile(fileId);
      await refreshFiles();
      message.success("上传文件已删除。");
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setDeletingId(null);
    }
  };

  const previewColumns = useMemo(
    () => (parsedTable?.headers ?? []).slice(0, 8).map((header) => ({ title: header, dataIndex: header, ellipsis: true, width: 140 })),
    [parsedTable],
  );

  return (
    <div className="page-stack">
      <Alert
        type="info"
        showIcon
        message="表格不用先改成固定模板"
        description="选择 CSV / XLSX 后会先读取表头；系统自动匹配，匹配不准时由你手动指定对应列。"
      />

      <div className="upload-flex-grid">
        <div>
          <Typography.Text strong>选择数据类型</Typography.Text>
          <Select
            value={selectedKind}
            options={fileKindOptions}
            style={{ width: "100%", marginTop: 8 }}
            onChange={(value) => applyKind(value)}
          />
          <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>
            无需固定表头：选择文件后自动匹配字段，匹配不准可手动指定
          </Typography.Paragraph>
        </div>
        <div>
          <Typography.Text strong>上传文件</Typography.Text>
          <Upload.Dragger
            accept=".csv,.xlsx"
            multiple={false}
            maxCount={1}
            fileList={pendingFiles}
            beforeUpload={(file) => { void preparePendingFile(file); return false; }}
            onRemove={() => { clearPending(); return true; }}
            style={{ marginTop: 8 }}
          >
            <p>{parsingFile || uploading ? "正在读取文件……" : "拖拽文件到这里，或点击选择 CSV / XLSX 文件"}</p>
          </Upload.Dragger>
        </div>
      </div>

      <Modal
        title="上传前确认列对应"
        open={mappingOpen && !!parsedTable}
        onCancel={clearPending}
        onOk={() => void handleConfirmUpload()}
        okText="确认并上传"
        cancelText="取消"
        confirmLoading={uploading}
        okButtonProps={{ disabled: missingRequired.length > 0 || parsingFile }}
        width={920}
        destroyOnHidden
      >
        {parsedTable ? (
          <div className="column-mapping-card" style={{ marginTop: 8 }}>
            <div className="mapping-header">
              <div>
                <Typography.Text type="secondary">
                  已读取 {parsedTable.rows.length} 行、{parsedTable.headers.length} 列。原表头不用改名，确认后系统会直接上传并解析。
                </Typography.Text>
              </div>
              <Space wrap>
                <Tag color="blue">{formatFileKind(selectedKind)}</Tag>
                {missingRequired.length ? <Tag color="red">还有 {missingRequired.length} 项需确认</Tag> : <Tag color="green">可以上传</Tag>}
              </Space>
            </div>

            <div className="mapping-grid">
              {fields.map((field) => {
                const options = [
                  ...parsedTable.headers.map((header) => ({ label: `文件列：${header}`, value: header })),
                  ...(field.autoOptions ?? []),
                ];
                return (
                  <div key={field.key} className={`mapping-item ${field.required && !columnMapping[field.key] ? "mapping-item-missing" : ""}`}>
                    <div className="mapping-label">
                      <Typography.Text strong>{field.label}</Typography.Text>
                      <Typography.Text type="secondary">{field.required ? "必需" : "可选"}</Typography.Text>
                    </div>
                    <Select
                      allowClear={!field.required}
                      placeholder={field.required ? "选择文件中的对应列" : "可不使用"}
                      value={columnMapping[field.key] || undefined}
                      options={options}
                      showSearch
                      optionFilterProp="label"
                      style={{ width: "100%" }}
                      onChange={(value) => setColumnMapping((current) => ({ ...current, [field.key]: value ?? "" }))}
                    />
                  </div>
                );
              })}
            </div>

            <Typography.Text strong>原文件预览（前 3 行）</Typography.Text>
            <Table
              size="small"
              rowKey={(_, index) => String(index)}
              columns={previewColumns}
              dataSource={parsedTable.rows.slice(0, 3)}
              pagination={false}
              scroll={{ x: "max-content" }}
              style={{ marginTop: 8 }}
            />
          </div>
        ) : null}
      </Modal>

      <Table
        rowKey="id"
        dataSource={files}
        pagination={false}
        locale={{ emptyText: "当前还没有上传文件。" }}
        columns={[
          { title: "文件名", dataIndex: "original_name" },
          { title: "数据类型", dataIndex: "file_kind", render: (value: FileKind) => formatFileKind(value) },
          { title: "解析状态", dataIndex: "parse_status", render: (value) => <ParseStatusTag status={value} /> },
          { title: "记录数", dataIndex: "row_count" },
          { title: "错误信息", dataIndex: "error_message", render: (value: string | null) => value || "-" },
          {
            title: "操作",
            key: "actions",
            render: (_, record) => (
              <Button type="link" danger loading={deletingId === record.id} onClick={() => handleDelete(record.id)}>删除</Button>
            ),
          },
        ]}
      />
    </div>
  );
}
