/**
 * 本文件的作用是：封装前端访问教学分段后端接口的方法。
 */
import { apiRequest } from "./client";
import type { ApiMessage, AutoSegmentBuildResult, TeachingSegmentItem } from "../types/api";

export interface SegmentPayload {
  knowledge_point_id?: number | null;
  title: string;
  start_minute: number;
  end_minute: number;
  display_order?: number;
  teacher_notes?: string;
}

export function createSegment(sessionId: number, payload: SegmentPayload): Promise<TeachingSegmentItem> {
  return apiRequest(`/api/v1/sessions/${sessionId}/segments`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function autoBuildSegments(
  sessionId: number,
  payload?: { replace_existing?: boolean },
): Promise<AutoSegmentBuildResult> {
  return apiRequest(`/api/v1/sessions/${sessionId}/segments/auto-build`, {
    method: "POST",
    body: JSON.stringify(payload ?? {}),
  });
}

export function updateSegment(segmentId: number, payload: Partial<SegmentPayload>): Promise<TeachingSegmentItem> {
  return apiRequest(`/api/v1/segments/${segmentId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteSegment(segmentId: number): Promise<ApiMessage> {
  return apiRequest(`/api/v1/segments/${segmentId}`, { method: "DELETE" });
}
