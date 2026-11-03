# 数据模板

支持 CSV、XLSX、XLSM。CSV 推荐 UTF-8，GBK/GB18030 也会尝试识别。

## quiz

必填：

```text
student_code,question_code,score,is_correct,event_minute
```

可选：`student_name`

## submission

必填：

```text
student_code,task_name,language,result_status,event_minute
```

可选：`student_name,error_type,error_message`

## interaction

必填：

```text
student_code,event_type,event_minute
```

可选：`student_name,value`

## transcript

必填：

```text
start_minute,end_minute,text
```

可选：`speaker`

## ppt_timeline

必填：

```text
slide_index,start_minute,end_minute
```

可选：`slide_title`

## 时间字段

统一使用“从本节课开始算起的分钟数”，允许小数，例如 `12.5`。

## 一键 ZIP

ZIP 中可同时放五类文件。文件名只要包含对应英文/中文关键词即可，例如：

```text
课堂测验_quiz.csv
编程提交_submission.csv
interaction.csv
课堂讲稿_transcript.csv
ppt_timeline.csv
```

每种类型只能有一份。

可选 `manifest.json`：

```json
{
  "knowledge_points": [
    {"name": "条件判断", "topic_area": "Python 基础"},
    {"name": "while 循环", "topic_area": "Python 基础"}
  ]
}
```

## 测试和现场演示

- 20 组大样本：`demo_data/批量测试数据/`
- 现场演示：`demo_data/现场演示_手动输入版/`
- 一键演示包：`demo_data/现场演示_手动输入版/现场演示一键导入.zip`
