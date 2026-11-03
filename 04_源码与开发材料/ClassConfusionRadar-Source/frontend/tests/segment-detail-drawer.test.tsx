/**
 * 本文件的作用是：验证分段详情抽屉展示评分证据、错误信息和干预操作。
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SegmentDetailDrawer } from "../src/features/analytics/SegmentDetailDrawer";
import type { SegmentAnalyticsDetail } from "../src/types/api";

const detail: SegmentAnalyticsDetail = {
  segment_score_id: 11,
  segment_id: 1,
  session_id: 3,
  title: "循环条件判断",
  knowledge_point_name: "while 循环",
  start_minute: 10,
  end_minute: 30,
  teacher_notes: "重点观察循环出口条件",
  confusion_score: 66.67,
  risk_level: "high",
  score_formula: "困惑得分 = 35%×测验错误率 + 35%×提交失败率 + 20%×错误密度 + 10%×互动沉默度",
  signal_breakdown: [
    {
      key: "quiz_incorrect_rate",
      label: "测验错误率",
      weight_percent: 35,
      raw_value: 0.6667,
      value_percent: 66.67,
      contribution_score: 23.33,
      samples: 3,
      description: "本段课堂测验中错误作答的占比。",
      evidence_summary: "本段测验作答 3 次，其中错误 2 次。",
    },
    {
      key: "submission_failure_rate",
      label: "提交失败率",
      weight_percent: 35,
      raw_value: 0.3333,
      value_percent: 33.33,
      contribution_score: 11.67,
      samples: 3,
      description: "本段编程提交中非 success 结果的占比。",
      evidence_summary: "本段编程提交 3 次，其中失败 1 次。",
    },
  ],
  error_summary: [{ label: "SyntaxError", count: 2 }],
  main_error_summary: "SyntaxError × 2",
  overall_explanation: "该分段困惑得分为 66.67，判定为高风险，主要由 测验错误率 66.67%（贡献 23.33 分）拉高。",
  generated_at: "2026-04-12T12:00:00Z",
};

describe("SegmentDetailDrawer", () => {
  it("shows explainability fields in a one-glance layout", () => {
    render(<SegmentDetailDrawer open loading={false} detail={detail} onClose={() => undefined} />);

    expect(screen.getByText("一句话解释")).toBeTruthy();
    expect(screen.getByText("首要拉高信号")).toBeTruthy();
    expect(screen.getAllByText("测验错误率").length).toBeGreaterThan(0);
    expect(screen.getAllByText("语法错误 × 2").length).toBeGreaterThan(0);
    expect(screen.getByText("本段测验作答 3 次，其中错误 2 次。")).toBeTruthy();
  });
});
