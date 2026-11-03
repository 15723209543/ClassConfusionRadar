/**
 * 本文件的作用是：封装前端访问enhancedanalytics后端接口的方法。
 */
import { apiRequest } from "./client";
import type {
  EnhanceAnalysisRequest,
  EnhancedSegmentAnalysis,
  EnhancedSessionAnalysis,
} from "../types/api";

export function getSessionEnhancedAnalysis(sessionId: number): Promise<EnhancedSessionAnalysis> {
  return apiRequest(`/api/v1/sessions/${sessionId}/analytics/enhance`);
}

export function createSessionEnhancedAnalysis(
  sessionId: number,
  payload: EnhanceAnalysisRequest = {},
): Promise<EnhancedSessionAnalysis> {
  return apiRequest(`/api/v1/sessions/${sessionId}/analytics/enhance`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSegmentEnhancedAnalysis(segmentScoreId: number): Promise<EnhancedSegmentAnalysis> {
  return apiRequest(`/api/v1/segment-scores/${segmentScoreId}/analytics/enhance`);
}

export function createSegmentEnhancedAnalysis(
  segmentScoreId: number,
  payload: EnhanceAnalysisRequest = {},
): Promise<EnhancedSegmentAnalysis> {
  return apiRequest(`/api/v1/segment-scores/${segmentScoreId}/analytics/enhance`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
