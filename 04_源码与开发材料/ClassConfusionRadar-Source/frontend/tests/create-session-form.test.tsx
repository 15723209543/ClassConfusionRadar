/**
 * 本文件的作用是：验证创建课堂表单的默认值、课程类型和提交数据。
 */
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CreateSessionForm } from "../src/features/sessions/CreateSessionForm";

describe("CreateSessionForm", () => {
  it("submits default values with a custom title", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(<CreateSessionForm loading={false} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByPlaceholderText("例如：Python 条件语句与循环"), {
      target: { value: "测试课堂" },
    });
    fireEvent.click(screen.getByRole("button", { name: "创建并进入工作台" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "测试课堂",
          course_type: "python",
          duration_minutes: 90,
        }),
      );
    });
  });
});
