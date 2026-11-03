/**
 * 本文件的作用是：验证增强课堂解读的结构化结论与分段查看入口。
 */
import { App } from "antd";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EnhancedSessionAnalysisPanel } from "../src/features/analytics/EnhancedSessionAnalysisPanel";

const getSessionEnhancedAnalysis = vi.fn();
const createSessionEnhancedAnalysis = vi.fn();

vi.mock("../src/api/enhancedAnalytics", () => ({
  getSessionEnhancedAnalysis: (...args: unknown[]) => getSessionEnhancedAnalysis(...args),
  createSessionEnhancedAnalysis: (...args: unknown[]) => createSessionEnhancedAnalysis(...args),
}));

describe("EnhancedSessionAnalysisPanel", () => {
  it("renders structured enhanced insights and can inspect the linked segment", async () => {
    const onInspectSegment = vi.fn();

    getSessionEnhancedAnalysis.mockResolvedValue({
      id: 2,
      analysis_run_id: 9,
      status: "ready",
      model_name: "offline-enhanced-v2",
      generation_mode: "offline_rule",
      generation_mode_label: "离线解释",
      prompt_version: "v1_enhanced_session",
      summary: "This class has one clearly elevated loop segment that deserves reteaching.",
      teacher_takeaways: ["Review loop-exit conditions first."],
      top_segment_insights: [
        {
          segment_score_id: 11,
          segment_id: 7,
          title: "Loop practice window",
          why_high_risk: "Submission failures cluster around loop boundaries.",
          teacher_focus: "Put loop boundaries and exit conditions on the board together.",
        },
      ],
      citations: [
        {
          title: "Transcript excerpt 1",
          url: null,
          source_type: "uploaded_transcript",
          excerpt: "Today we compare while loops and for loops.",
        },
      ],
      memory_notes: ["Keep the explanation consistent with the top high-risk segment."],
      generated_at: "2026-04-17T10:00:00Z",
      failure_reason: null,
      created_at: "2026-04-17T10:00:00Z",
      updated_at: "2026-04-17T10:00:00Z",
    });

    render(
      <App>
        <EnhancedSessionAnalysisPanel sessionId={5} hasAnalysis onInspectSegment={onInspectSegment} />
      </App>,
    );

    await waitFor(() => {
      expect(getSessionEnhancedAnalysis).toHaveBeenCalledWith(5);
    });

    expect(screen.getByText("API 增强分析")).toBeTruthy();
    expect(screen.getByText("This class has one clearly elevated loop segment that deserves reteaching.")).toBeTruthy();
    expect(screen.getByText("Review loop-exit conditions first.")).toBeTruthy();
    expect(screen.getByText("Loop practice window")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "查看对应分段" }));
    expect(onInspectSegment).toHaveBeenCalledWith(7);
  });
});
