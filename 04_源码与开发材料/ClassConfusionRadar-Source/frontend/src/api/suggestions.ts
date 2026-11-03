/**
 * 本文件的作用是：封装前端访问再教学建议后端接口的方法。
 */
import { apiRequest } from "./client";
import type { ReteachingSuggestion } from "../types/api";

export function createSuggestion(segmentScoreId: number): Promise<ReteachingSuggestion> {
  return apiRequest(`/api/v1/segment-scores/${segmentScoreId}/suggestions`, {
    method: "POST",
  });
}

export function getSuggestion(segmentScoreId: number): Promise<ReteachingSuggestion> {
  return apiRequest(`/api/v1/segment-scores/${segmentScoreId}/suggestions`);
}
