/**
 * 本文件的作用是：提供可复用的 StatusTag 界面组件。
 */
import { Tag } from "antd";
import type { ParseStatus, RiskLevel, SessionStatus } from "../types/api";

export function SessionStatusTag({ status }: { status: SessionStatus }) {
  const colorMap: Record<SessionStatus, string> = {
    draft: "default",
    ready: "processing",
    analyzed: "success",
  };
  const labelMap: Record<SessionStatus, string> = {
    draft: "待完善",
    ready: "可分析",
    analyzed: "已分析",
  };
  return <Tag color={colorMap[status]}>{labelMap[status]}</Tag>;
}

export function ParseStatusTag({ status }: { status: ParseStatus }) {
  const colorMap: Record<ParseStatus, string> = {
    pending: "default",
    processing: "processing",
    success: "success",
    failed: "error",
  };
  const labelMap: Record<ParseStatus, string> = {
    pending: "待处理",
    processing: "处理中",
    success: "解析成功",
    failed: "解析失败",
  };
  return <Tag color={colorMap[status]}>{labelMap[status]}</Tag>;
}

export function RiskLevelTag({ riskLevel }: { riskLevel: RiskLevel }) {
  const colorMap: Record<RiskLevel, string> = {
    low: "green",
    medium: "gold",
    high: "orange",
    critical: "red",
  };
  const labelMap: Record<RiskLevel, string> = {
    low: "低风险",
    medium: "中风险",
    high: "高风险",
    critical: "极高风险",
  };
  return <Tag color={colorMap[riskLevel]}>{labelMap[riskLevel]}</Tag>;
}
