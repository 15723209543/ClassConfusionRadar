/**
 * 本文件的作用是：封装前端访问困惑评分与证据汇总后端接口的方法。
 */
import { API_BASE_URL, apiRequest } from "./client";
import type {
  AnalysisRun,
  AnalyticsOverview,
  ReteachingInterventionCreate,
  ReteachingInterventionRead,
  SegmentAnalyticsDetail,
} from "../types/api";

export function runAnalytics(sessionId: number): Promise<AnalysisRun> {
  return apiRequest(`/api/v1/sessions/${sessionId}/analytics/run`, { method: "POST" });
}

export function getAnalyticsOverview(sessionId: number): Promise<AnalyticsOverview> {
  return apiRequest(`/api/v1/sessions/${sessionId}/analytics/overview`);
}

export function getSegmentAnalytics(segmentId: number): Promise<SegmentAnalyticsDetail> {
  return apiRequest(`/api/v1/segments/${segmentId}/analytics`);
}

export async function downloadAnalyticsReport(sessionId: number): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/analytics/report.md`);
  if (!response.ok) {
    const payload = await response.text().catch(() => "");
    throw new Error(payload || "课堂复盘报告导出失败。");
  }
  return response.text();
}


export function getPrintableAnalyticsReportUrl(sessionId: number): string {
  return `${API_BASE_URL}/api/v1/sessions/${sessionId}/analytics/report.html`;
}

export function createReteachingIntervention(
  segmentScoreId: number,
  payload: ReteachingInterventionCreate,
): Promise<ReteachingInterventionRead> {
  return apiRequest(`/api/v1/segment-scores/${segmentScoreId}/interventions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getLatestReteachingIntervention(segmentScoreId: number): Promise<ReteachingInterventionRead> {
  return apiRequest(`/api/v1/segment-scores/${segmentScoreId}/interventions/latest`);
}


export function verifyReteachingIntervention(interventionId: number): Promise<ReteachingInterventionRead> {
  return apiRequest(`/api/v1/interventions/${interventionId}/verify`, { method: "POST" });
}
