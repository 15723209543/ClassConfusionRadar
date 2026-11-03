/**
 * 本文件的作用是：封装前端访问knowledgepoints后端接口的方法。
 */
import { apiRequest } from "./client";
import type { ApiMessage, KnowledgePointItem } from "../types/api";

export interface KnowledgePointPayload {
  name: string;
  topic_area?: string;
  description?: string;
  display_order?: number;
}

export function createKnowledgePoint(sessionId: number, payload: KnowledgePointPayload): Promise<KnowledgePointItem> {
  return apiRequest(`/api/v1/sessions/${sessionId}/knowledge-points`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateKnowledgePoint(
  knowledgePointId: number,
  payload: Partial<KnowledgePointPayload>,
): Promise<KnowledgePointItem> {
  return apiRequest(`/api/v1/knowledge-points/${knowledgePointId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteKnowledgePoint(knowledgePointId: number): Promise<ApiMessage> {
  return apiRequest(`/api/v1/knowledge-points/${knowledgePointId}`, { method: "DELETE" });
}
