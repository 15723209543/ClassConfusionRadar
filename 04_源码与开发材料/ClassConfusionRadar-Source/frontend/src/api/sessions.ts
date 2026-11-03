/**
 * 本文件的作用是：封装前端访问课堂场次后端接口的方法。
 */
import { apiRequest } from "./client";
import type { ApiMessage, SessionDetail, SessionSummary } from "../types/api";

export interface SessionPayload {
  title: string;
  course_type: string;
  class_date: string;
  duration_minutes: number;
  notes?: string;
}

export function listSessions(): Promise<SessionSummary[]> {
  return apiRequest("/api/v1/sessions");
}

export function createSession(payload: SessionPayload): Promise<SessionSummary> {
  return apiRequest("/api/v1/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSession(sessionId: number): Promise<SessionDetail> {
  return apiRequest(`/api/v1/sessions/${sessionId}`);
}

export function updateSession(sessionId: number, payload: Partial<SessionPayload>): Promise<SessionSummary> {
  return apiRequest(`/api/v1/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteSession(sessionId: number): Promise<ApiMessage> {
  return apiRequest(`/api/v1/sessions/${sessionId}`, { method: "DELETE" });
}
