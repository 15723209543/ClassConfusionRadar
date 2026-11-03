/**
 * 本文件的作用是：实现 BuiltinDatasetFloat 对应的前端交互与界面展示。
 */
import { useState } from "react";
import { App, Button, Modal, Select, Space, Typography } from "antd";
import { uploadDatasetZip } from "../../api/files";
import { BUILTIN_DATASETS } from "../../data/builtinDatasets";

interface BuiltinDatasetFloatProps {
  sessionId: number;
  onRefresh: () => Promise<void>;
}

function fileFromBase64(base64: string, filename: string): File {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return new File([bytes], filename, { type: "application/zip" });
}

export function BuiltinDatasetFloat({ sessionId, onRefresh }: BuiltinDatasetFloatProps) {
  const { message } = App.useApp();
  const [open, setOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(BUILTIN_DATASETS[0]?.id ?? "");
  const [uploading, setUploading] = useState(false);
  const selected = BUILTIN_DATASETS.find((item) => item.id === selectedId);

  const handleImport = async () => {
    if (!selected) return;
    try {
      setUploading(true);
      const file = fileFromBase64(selected.zipBase64, `${selected.id}_${selected.label.replace(/\s|·/g, "_")}.zip`);
      const result = await uploadDatasetZip(sessionId, file);
      await onRefresh();
      setOpen(false);
      message.success(`“${selected.label}”已导入：${result.uploaded_files.length} 类数据，共约 ${selected.records} 条记录。`);
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <Button className="builtin-dataset-float" type="primary" onClick={() => setOpen(true)}>
        内置测试数据
      </Button>
      <Modal
        title="内置测试数据"
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Typography.Paragraph type="secondary">
          共 20 组课堂数据，选择一组后可直接导入当前课堂。
        </Typography.Paragraph>
        <Select
          value={selectedId}
          style={{ width: "100%" }}
          options={BUILTIN_DATASETS.map((item) => ({
            value: item.id,
            label: `${item.id} · ${item.label}（${item.records} 条）`,
          }))}
          onChange={setSelectedId}
        />
        {selected ? (
          <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
            {selected.description}
          </Typography.Paragraph>
        ) : null}
        <Space style={{ width: "100%", justifyContent: "flex-end", marginTop: 12 }}>
          <Button onClick={() => setOpen(false)}>关闭</Button>
          <Button type="primary" loading={uploading} onClick={() => void handleImport()}>
            导入当前课堂
          </Button>
        </Space>
      </Modal>
    </>
  );
}
