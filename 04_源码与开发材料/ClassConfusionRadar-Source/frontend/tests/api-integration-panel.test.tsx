/**
 * 本文件的作用是：验证课堂解读面板以教师可理解的方式展示分析说明。
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApiIntegrationPanel } from "../src/features/analytics/ApiIntegrationPanel";
import type { AnalyticsOverview } from "../src/types/api";

const overview: AnalyticsOverview = {
  has_analysis: true,
  latest_run_id: 1,
  generated_at: "2026-04-17T12:00:00Z",
  score_formula: "score formula",
  scoring_rules: [],
  summary: {
    average_score: 27.5,
    high_risk_count: 0,
    critical_count: 0,
    total_segments: 2,
  },
  heatmap_cells: [
    {
      segment_id: 8,
      segment_title: "Mario",
      signal_key: "submission_failure_rate",
      signal_label: "提交失败率",
      value: 50,
    },
    {
      segment_id: 9,
      segment_title: "Summing Up",
      signal_key: "error_density",
      signal_label: "错误密度",
      value: 50,
    },
  ],
  top_errors: [],
  high_risk_segments: [],
};

vi.mock("../src/features/analytics/EnhancedSessionAnalysisPanel", () => ({
  EnhancedSessionAnalysisPanel: () => <div>mock enhanced session panel</div>,
}));

describe("ApiIntegrationPanel", () => {
  it("shows teacher-facing classroom explanations without developer tools", () => {
    const onInspectSegment = vi.fn();

    render(<ApiIntegrationPanel sessionId={3} overview={overview} onInspectSegment={onInspectSegment} />);

    expect(screen.getByText("这页是做什么的？")).toBeTruthy();
    expect(screen.getByText(/这里把困惑分数、主要错误、讲稿和 PPT 证据整理成课堂结论/)).toBeTruthy();
    expect(screen.getByText("mock enhanced session panel")).toBeTruthy();
    expect(screen.getByText("Mario")).toBeTruthy();
    expect(screen.getAllByText("可查看增强解释").length).toBeGreaterThan(0);
    expect(screen.queryByText("开发者工具（一般教学使用不需要）")).toBeNull();
  });
});
