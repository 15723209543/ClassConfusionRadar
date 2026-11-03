# public-demo 说明

这组样例用于证明系统可以接入公开来源的真实材料，不替换现有 `competition-demo`。

## 文件内容

- `transcript_demo.csv`
  - 来源：CS50 Python Week 2 Loops 公开 transcript
  - 用途：自动教学分段、增强分析引用
- `ppt_timeline_demo.csv`
  - 来源：CS50 Notes 页面章节标题
  - 用途：自动教学分段、slide window 对齐
- `submission_demo.csv`
  - 来源：AIZU Online Judge 公开 recent submissions feed
  - 用途：真实编程提交信号
- `SOURCES.md`
  - 记录公开来源、抓取时间、许可说明和字段派生策略

## 为什么没有 quiz / interaction

公开来源没有一套可直接复用的“单课堂真实 quiz 响应日志”和“课堂互动日志”，因此 `public-demo` 只导入：

- `transcript`
- `ppt_timeline`
- `submission`

系统在规则评分时会把缺失的 `quiz` 和 `interaction` 信号按 `0` 处理，并在信号解释里明确标注。

## 如何重新生成样例

在仓库根目录执行：

```powershell
python .\scripts\sync_public_demo_data.py
```

脚本会联网抓取公开来源并重新写入本目录下的 CSV 和 `SOURCES.md`。

## 如何导入本地系统

先确保后端已启动，然后执行：

```powershell
python .\scripts\public_demo_seed.py --base-url http://127.0.0.1:8000 --run-analytics --generate-enhanced
```

脚本会自动：

1. 创建 `Public Demo · CS50 Loops with AIZU Submissions`
2. 创建知识点
3. 上传真实公开样例文件
4. 自动生成教学分段
5. 运行规则分析
6. 生成课堂增强总览
7. 生成一个“高风险或最高分”的分段增强详情
