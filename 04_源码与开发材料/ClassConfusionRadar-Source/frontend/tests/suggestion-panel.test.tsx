/**
 * 本文件的作用是：验证教学建议面板按教师使用场景展示结构化建议内容。
 */
import { App } from "antd";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SuggestionPanel } from "../src/features/suggestions/SuggestionPanel";

const getSuggestion = vi.fn();
const createSuggestion = vi.fn();

vi.mock("../src/api/suggestions", () => ({
  getSuggestion: (...args: unknown[]) => getSuggestion(...args),
  createSuggestion: (...args: unknown[]) => createSuggestion(...args),
}));

describe("SuggestionPanel", () => {
  it("renders structured suggestion sections for teachers", async () => {
    getSuggestion.mockResolvedValue({
      id: 7,
      segment_score_id: 11,
      status: "ready",
      model_name: "offline-rules-v2",
      generation_mode: "offline_rule",
      generation_mode_label: "离线可解释建议",
      prompt_version: "v2_structured",
      structured_content: {
        diagnosis: "学生在循环条件判断上存在群体性困惑，主要表现为边界条件判断不稳定。",
        reteach_script: ["先重申循环出口条件。", "再对比正确与错误示例。"],
        board_plan: ["板书知识点标题。", "板书正确流程。"],
        micro_exercises: ["修正一段错误代码。", "预测条件变化后的输出。"],
        followup_task: "课后完成一题同构小题，并写出判断依据。",
      },
      suggestion_markdown: "## 再教学建议",
      failure_reason: null,
      generated_at: "2026-04-12T12:00:00Z",
      created_at: "2026-04-12T12:00:00Z",
      updated_at: "2026-04-12T12:00:00Z",
    });

    render(
      <App>
        <SuggestionPanel
          highRiskSegments={[
            {
              segment_score_id: 11,
              segment_id: 3,
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
              overall_explanation: "该分段主要由测验错误率和提交失败率拉高。",
            },
          ]}
        />
      </App>,
    );

    await waitFor(() => {
      expect(getSuggestion).toHaveBeenCalledWith(11);
    });

    expect(screen.getByText("诊断")).toBeTruthy();
    expect(screen.getByText("重讲脚本")).toBeTruthy();
    expect(screen.getByText("板书规划")).toBeTruthy();
    expect(screen.getByText("微练习")).toBeTruthy();
    expect(screen.getByText("跟进任务")).toBeTruthy();
    expect(screen.getByText("学生在循环条件判断上存在群体性困惑，主要表现为边界条件判断不稳定。")).toBeTruthy();
  });
});
