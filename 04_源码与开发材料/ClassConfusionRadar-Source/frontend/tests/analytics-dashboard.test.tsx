/**
 * 本文件的作用是：验证困惑分析面板正确展示评分规则、风险分段和解释信息。
 */
import { fireEvent, render, screen } from "@testing-library/react";
import type { CSSProperties } from "react";
import { describe, expect, it, vi } from "vitest";
import { AnalyticsDashboard } from "../src/features/analytics/AnalyticsDashboard";
import type { AnalyticsOverview } from "../src/types/api";

vi.mock("echarts-for-react", () => ({
  default: ({ style }: { style?: CSSProperties }) => <div data-testid="mock-chart" style={style} />,
}));

const overview: AnalyticsOverview = {
  has_analysis: true,
  latest_run_id: 1,
  generated_at: "2026-04-12T12:00:00Z",
  score_formula: "困惑得分 = 35%×测验错误率 + 35%×提交失败率 + 20%×错误密度 + 10%×互动沉默度",
  scoring_rules: [
    { key: "quiz_incorrect_rate", label: "测验错误率", weight_percent: 35, description: "测验中错误作答的占比。" },
    { key: "submission_failure_rate", label: "提交失败率", weight_percent: 35, description: "提交失败的占比。" },
    { key: "error_density", label: "错误密度", weight_percent: 20, description: "带错误信息提交的占比。" },
    { key: "interaction_silence", label: "互动沉默度", weight_percent: 10, description: "没有参与互动的学生占比。" },
  ],
  summary: {
    average_score: 67.5,
    high_risk_count: 1,
    critical_count: 0,
    total_segments: 2,
  },
  heatmap_cells: [
    { segment_id: 1, segment_title: "循环条件判断", signal_key: "quiz_incorrect_rate", signal_label: "测验错误率", value: 66.67 },
    { segment_id: 1, segment_title: "循环条件判断", signal_key: "submission_failure_rate", signal_label: "提交失败率", value: 66.67 },
  ],
  top_errors: [{ label: "SyntaxError", count: 2 }],
  high_risk_segments: [
    {
      segment_score_id: 11,
      segment_id: 1,
      title: "循环条件判断",
      knowledge_point_name: "while 循环",
      start_minute: 10,
      end_minute: 30,
      confusion_score: 66.67,
      risk_level: "high",
      primary_signal_label: "测验错误率",
      primary_signal_value_percent: 66.67,
      primary_signal_contribution_score: 23.33,
      main_error_summary: "SyntaxError × 2",
      overall_explanation: "该分段困惑得分为 66.67，判定为高风险，主要由 测验错误率 66.67%（贡献 23.33 分）拉高。",
    },
  ],
};

describe("AnalyticsDashboard", () => {
  it("renders scoring formula and explanation for judges to scan quickly", () => {
    const onInspectSegment = vi.fn();

    render(<AnalyticsDashboard sessionId={3} overview={overview} onInspectSegment={onInspectSegment} />);

    expect(screen.getByText("评分规则一眼看懂")).toBeTruthy();
    expect(screen.getByText(/困惑得分 = 35%×测验错误率/)).toBeTruthy();
    expect(screen.getAllByText("高风险分段").length).toBeGreaterThan(0);
    expect(
      screen.getAllByText((_, element) => (element?.textContent ?? "").includes("该分段困惑得分为 66.67")).length,
    ).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "查看详情" }));
    expect(onInspectSegment).toHaveBeenCalledWith(1);
  });
});
