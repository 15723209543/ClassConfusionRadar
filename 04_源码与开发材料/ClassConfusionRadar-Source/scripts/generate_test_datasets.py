"""
本文件的作用是：生成并校验项目使用的合成测试数据。
"""
from __future__ import annotations

import csv
import json
import random
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo_data"

SCENARIOS = [
    ("01_Python_条件与循环", "Python 程序设计", ["条件判断", "while 循环", "for 循环", "循环边界", "调试方法"], 3, "OffByOne"),
    ("02_Python_函数与参数", "Python 程序设计", ["函数定义", "参数传递", "返回值", "变量作用域", "递归入口"], 4, "ScopeError"),
    ("03_C_数组与指针", "C 语言程序设计", ["数组下标", "指针基础", "指针与数组", "字符串", "越界访问"], 2, "SegmentationFault"),
    ("04_数据结构_栈与队列", "数据结构", ["栈操作", "队列操作", "循环队列", "括号匹配", "表达式求值"], 2, "QueueBoundary"),
    ("05_数据结构_链表", "数据结构", ["结点结构", "链表插入", "链表删除", "头结点", "内存释放"], 2, "NullPointer"),
    ("06_算法_二分查找", "算法设计", ["有序性", "区间定义", "中点计算", "边界更新", "复杂度"], 3, "BoundaryUpdate"),
    ("07_算法_递归与回溯", "算法设计", ["递归状态", "终止条件", "递归返回", "回溯恢复", "剪枝"], 1, "MissingBaseCase"),
    ("08_Cpp_类与对象", "C++ 程序设计", ["类定义", "构造函数", "成员访问", "继承", "虚函数"], 4, "VirtualDispatch"),
    ("09_SQL_连接查询", "数据库基础", ["SELECT 基础", "WHERE 条件", "INNER JOIN", "LEFT JOIN", "聚合分组"], 2, "JoinCondition"),
    ("10_Web_API与异步", "Web 编程", ["HTTP 请求", "状态码", "JSON 解析", "异步调用", "异常处理"], 3, "AsyncOrder"),
    ("11_Java_集合框架", "Java 程序设计", ["List 接口", "Set 集合", "Map 映射", "迭代器", "泛型约束"], 2, "ConcurrentModification"),
    ("12_操作系统_进程与线程", "操作系统", ["进程状态", "线程模型", "进程调度", "同步互斥", "死锁预防"], 3, "RaceCondition"),
    ("13_计算机网络_TCP可靠传输", "计算机网络", ["TCP 连接", "序列号", "确认机制", "流量控制", "拥塞控制"], 2, "SequenceMismatch"),
    ("14_数据库_事务与并发", "数据库原理", ["事务特性", "并发异常", "隔离级别", "锁机制", "日志恢复"], 2, "IsolationViolation"),
    ("15_软件工程_设计模式", "软件工程", ["单一职责", "工厂模式", "观察者模式", "策略模式", "依赖倒置"], 4, "DependencyInversion"),
    ("16_人工智能_搜索算法", "人工智能导论", ["状态空间", "广度优先", "深度优先", "启发函数", "A星搜索"], 3, "HeuristicError"),
    ("17_机器学习_分类模型", "机器学习", ["特征处理", "逻辑回归", "决策树", "模型评估", "过拟合"], 4, "Overfitting"),
    ("18_前端开发_React状态管理", "前端开发", ["组件状态", "属性传递", "副作用", "状态提升", "渲染优化"], 2, "EffectDependency"),
    ("19_信息安全_密码学基础", "信息安全", ["对称加密", "公钥密码", "哈希函数", "数字签名", "密钥管理"], 3, "SignatureMismatch"),
    ("20_嵌入式_传感器采集", "嵌入式系统", ["GPIO 接口", "ADC 采样", "定时器", "中断处理", "数据滤波"], 3, "InterruptConflict"),
]

ERROR_POOL = ["SyntaxError", "WrongAnswer", "RuntimeError", "BoundaryCondition", "StateUpdate"]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_dataset(
    folder: Path,
    title: str,
    course: str,
    topics: list[str],
    risk_index: int,
    risk_error: str,
    *,
    students: int,
    seed: int,
    class_date: str | None = None,
) -> None:
    rng = random.Random(seed)
    folder.mkdir(parents=True, exist_ok=True)
    duration = 90
    window = duration / len(topics)

    quiz_rows: list[dict] = []
    submission_rows: list[dict] = []
    interaction_rows: list[dict] = []
    transcript_rows: list[dict] = []
    ppt_rows: list[dict] = []

    for topic_index, topic in enumerate(topics):
        start = topic_index * window
        end = (topic_index + 1) * window
        for part in range(2):
            part_start = start + part * window / 2
            part_end = start + (part + 1) * window / 2
            slide_index = topic_index * 2 + part + 1
            ppt_rows.append({
                "slide_index": slide_index,
                "start_minute": round(part_start, 1),
                "end_minute": round(part_end, 1),
                "slide_title": topic,
            })
            transcript_rows.append({
                "start_minute": round(part_start, 1),
                "end_minute": round(part_end, 1),
                "speaker": "teacher",
                "text": f"这一段讲{topic}。先看基本规则，再用一个例子检查边界和常见错误。",
            })

    for student_no in range(1, students + 1):
        student_code = f"S{student_no:03d}"
        student_name = f"测试学生{student_no:03d}"
        for topic_index, topic in enumerate(topics):
            start = topic_index * window
            is_risk = topic_index == risk_index
            base_error = 0.18 + (0.48 if is_risk else 0.0)
            correct = rng.random() > base_error
            quiz_rows.append({
                "student_code": student_code,
                "student_name": student_name,
                "question_code": f"Q{topic_index + 1}",
                "score": 1 if correct else 0,
                "is_correct": "true" if correct else "false",
                "event_minute": round(start + 8.0 + rng.uniform(-1.2, 1.2), 1),
            })

            fail_rate = 0.15 + (0.52 if is_risk else 0.0)
            failed = rng.random() < fail_rate
            error_type = risk_error if is_risk else rng.choice(ERROR_POOL)
            result_status = "success" if not failed else "wrong_answer"
            submission_rows.append({
                "student_code": student_code,
                "student_name": student_name,
                "task_name": f"{topic}-练习",
                "language": "python" if "Python" in course or "Web" in course else "cpp",
                "result_status": result_status,
                "error_type": "" if not failed else error_type,
                "error_message": "" if not failed else f"{topic} 检查失败",
                "event_minute": round(start + 11.0 + rng.uniform(-1.0, 1.0), 1),
            })
            if failed and is_risk and rng.random() < 0.70:
                repeat_count = 1 + int(rng.random() < 0.35)
                for repeat in range(repeat_count):
                    submission_rows.append({
                        "student_code": student_code,
                        "student_name": student_name,
                        "task_name": f"{topic}-练习",
                        "language": "python" if "Python" in course or "Web" in course else "cpp",
                        "result_status": "wrong_answer",
                        "error_type": error_type,
                        "error_message": f"重复出现 {error_type}",
                        "event_minute": round(start + 12.2 + repeat * 0.8 + rng.uniform(-0.2, 0.2), 1),
                    })

            interaction_rate = 0.70 - (0.45 if is_risk else 0.0)
            if rng.random() < interaction_rate:
                interaction_rows.append({
                    "student_code": student_code,
                    "student_name": student_name,
                    "event_type": rng.choice(["poll", "raise_hand", "answer"]),
                    "value": 1,
                    "event_minute": round(start + 6.0 + rng.uniform(-1.5, 1.5), 1),
                })

    write_csv(folder / "quiz.csv", ["student_code", "student_name", "question_code", "score", "is_correct", "event_minute"], quiz_rows)
    write_csv(folder / "submission.csv", ["student_code", "student_name", "task_name", "language", "result_status", "error_type", "error_message", "event_minute"], submission_rows)
    write_csv(folder / "interaction.csv", ["student_code", "student_name", "event_type", "value", "event_minute"], interaction_rows)
    write_csv(folder / "transcript.csv", ["start_minute", "end_minute", "speaker", "text"], transcript_rows)
    write_csv(folder / "ppt_timeline.csv", ["slide_index", "start_minute", "end_minute", "slide_title"], ppt_rows)

    manifest = {
        "session": {
            "title": title,
            "course_type": course,
            "class_date": class_date or f"2026-09-{seed + 1:02d}",
            "duration_minutes": duration,
        },
        "knowledge_points": [
            {"name": topic, "topic_area": course, "display_order": index + 1}
            for index, topic in enumerate(topics)
        ],
        "data_note": "本数据集为项目测试用合成数据，不代表真实学生。",
        "expected_focus": topics[risk_index],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "README.md").write_text(
        f"# {title}\n\n"
        f"- 课程：{course}\n"
        f"- 学生数：{students}\n"
        f"- 重点风险知识点：{topics[risk_index]}\n"
        f"- 测验记录：{len(quiz_rows)}\n"
        f"- 提交记录：{len(submission_rows)}\n"
        f"- 互动记录：{len(interaction_rows)}\n"
        "- 数据性质：合成测试数据，仅用于功能验证和现场演示。\n",
        encoding="utf-8",
    )


def zip_dataset(folder: Path, output: Path) -> None:
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.name != output.name:
                archive.write(path, arcname=path.name)


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    bulk = OUT / "批量测试数据"
    for index, (name, course, topics, risk_index, risk_error) in enumerate(SCENARIOS, start=1):
        folder = bulk / name
        make_dataset(folder, name.replace("_", " "), course, topics, risk_index, risk_error, students=48, seed=index)
        zip_dataset(folder, folder / "一键导入.zip")

    live = OUT / "现场演示_手动输入版"
    live_topics = ["条件判断", "while 循环", "循环边界", "错误定位", "综合练习"]
    make_dataset(
        live,
        "现场演示：Python 条件与循环",
        "Python 程序设计",
        live_topics,
        2,
        "OffByOne",
        students=12,
        seed=20,
        class_date="2026-09-20",
    )
    zip_dataset(live, live / "现场演示一键导入.zip")
    (live / "现场演示输入卡.md").write_text(
        "# 现场演示输入卡\n\n"
        "## 新建课堂时手动输入\n\n"
        "- 课堂名称：现场演示：Python 条件与循环\n"
        "- 课程类型：Python 程序设计\n"
        "- 日期：2026-09-20\n"
        "- 时长：90 分钟\n"
        "- 备注：iCAN 现场演示数据\n\n"
        "## 演示顺序\n\n"
        "1. 新建课堂。\n"
        "2. 在“数据上传”中依次选择 quiz.csv、submission.csv、interaction.csv、transcript.csv、ppt_timeline.csv；程序会按文件名自动识别类型。\n"
        "3. 进入“教学分段”，执行自动生成分段。\n"
        "4. 运行困惑分析，重点查看“循环边界”。\n"
        "5. 打开分段详情，展示数据完整度、重复错误密度和再教学建议。\n"
        "6. 打开打印版课堂复盘报告，演示“另存为 PDF”。\n",
        encoding="utf-8",
    )

    total_rows = 0
    for csv_path in OUT.rglob("*.csv"):
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            total_rows += max(0, sum(1 for _ in handle) - 1)
    (OUT / "README.md").write_text(
        "# 测试与演示数据\n\n"
        "这里保留 20 组大样本测试数据和 1 组现场演示数据。所有学生记录均为程序生成的合成数据，"
        "不对应真实个人。每组数据都包含五类课堂数据和 `manifest.json`。\n\n"
        f"当前 CSV 数据总行数：{total_rows}。\n\n"
        "批量测试数据用于稳定性、缺失数据、重复错误和自动分段验证；现场演示包用于比赛现场快速操作。\n",
        encoding="utf-8",
    )
    print(f"generated: {OUT} ({total_rows} csv rows)")


if __name__ == "__main__":
    main()
