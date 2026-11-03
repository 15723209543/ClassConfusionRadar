# Public Demo Sources

- 生成时间：2026-04-17 09:08 UTC
- 说明：这套样例用于证明系统可以接入公开来源的真实材料；不替换现有 synthetic competition-demo。

## 1. 讲课材料来源
- Week page：https://cs50.harvard.edu/python/weeks/2/
- Transcript：https://cdn.cs50.net/python/2022/x/lectures/2/lang/en/lecture2.txt
- Notes：https://cs50.harvard.edu/python/notes/2/
- Google Slides：https://docs.google.com/presentation/d/1Dpqw4_EkV_EzSb7LC-Hy5ZQ-s0pflW0eS8GCZ4yxTnI/edit?usp=sharing
- 许可与使用：CS50 官方课程公开页面，仅用于本地课程分析演示和来源说明。

## 2. 编程提交来源
- AIZU 官方 recent submissions API：https://judgeapi.u-aizu.ac.jp/submission_records/recent
- 说明：AIZU Online Judge 是 IBM Project CodeNet README 明确列出的两大原始来源之一。
- Project CodeNet README：https://github.com/IBM/Project_CodeNet
- 许可与使用：公开 judge feed，仅提取少量近期 Python3 提交的元数据，不下载源码。

## 3. 字段转换说明
- transcript_demo.csv
  - 原始字段：CS50 transcript 文本段落
  - 派生字段：start_minute / end_minute 基于段落词数与 150 wpm 语速估算
  - 行数：18
- ppt_timeline_demo.csv
  - 原始字段：CS50 Notes 页面的 h2 section headings
  - 派生字段：start_minute / end_minute 通过 transcript 段落分桶对齐得到
  - 行数：9
- submission_demo.csv
  - 原始字段：AIZU API 的 judgeId / userId / problemId / problemTitle / status / submissionDate / language
  - 派生字段：student_code / student_name 进行了匿名化；event_minute 映射到课堂练习时间窗
  - 行数：7

## 4. 主题一致性说明
- 本 public-demo 以 CS50 Python Week 2 Loops 作为讲课材料主线。
- AIZU 选取的是 ITP1 初级题目中的条件判断与循环类 Python3 提交记录，作为“真实编程提交证据”补充。
- 因为公开来源中没有现成的单课堂 quiz / interaction 响应日志，本样例只导入 transcript + ppt_timeline + submission。
- 系统规则评分会按既有设计将缺失的 quiz / interaction 信号按 0 处理。
