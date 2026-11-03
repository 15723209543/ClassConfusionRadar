# Competition Demo Sample Pack

这组样例文件用于本地答辩演示，覆盖一条完整链路：

1. 创建课堂场次
2. 上传结构化课堂文件
3. 自动生成教学分段
4. 运行困惑分析
5. 生成再教学建议

## 文件说明

- `quiz_demo.csv`
  课堂小测结果，设计成 `while 循环` 和 `循环边界与调试` 两段风险更高。
- `submission_demo.csv`
  编程提交记录，包含 `SyntaxError`、`InfiniteLoop`、`BoundaryCondition` 等典型错误。
- `interaction_demo.csv`
  课堂互动记录，高风险分段的互动更少，用来拉开沉默度信号。
- `transcript_demo.csv`
  课堂讲稿时间轴，用于自动生成教学分段。
- `ppt_timeline_demo.csv`
  PPT 时间窗，用于自动生成教学分段。

## 手动上传建议顺序

如果你想在 UI 里完整演示“上传文件”步骤，推荐顺序如下：

1. `quiz_demo.csv`
2. `submission_demo.csv`
3. `interaction_demo.csv`
4. `transcript_demo.csv`
5. `ppt_timeline_demo.csv`

## 搭配的知识点

在“教学分段”页先创建以下 3 个知识点，再点击“自动生成分段”，效果最稳定：

1. `条件判断`
2. `while 循环`
3. `循环边界与调试`
