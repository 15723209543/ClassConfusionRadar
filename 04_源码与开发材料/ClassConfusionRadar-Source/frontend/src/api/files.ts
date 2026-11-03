/**
 * 本文件的作用是：封装前端访问课堂文件后端接口的方法。
 */
import { apiRequest } from "./client";
import type { ApiMessage, DatasetImportResult, FileKind, UploadedFileItem } from "../types/api";

export async function uploadSessionFile(
  sessionId: number,
  fileKind: FileKind,
  file: File,
): Promise<UploadedFileItem> {
  const formData = new FormData();
  formData.append("file_kind", fileKind);
  formData.append("file", file);

  return apiRequest(`/api/v1/sessions/${sessionId}/files`, {
    method: "POST",
    body: formData,
  });
}


export async function uploadDatasetZip(sessionId: number, file: File): Promise<DatasetImportResult> {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest(`/api/v1/sessions/${sessionId}/dataset-zip`, {
    method: "POST",
    body: formData,
  });
}

export function deleteUploadedFile(fileId: number): Promise<ApiMessage> {
  return apiRequest(`/api/v1/files/${fileId}`, { method: "DELETE" });
}
