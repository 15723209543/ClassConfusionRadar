/**
 * 本文件的作用是：提供文件处理或界面文本转换等通用工具。
 */
import type { FileKind } from "../types/api";

const courseTypeMap: Record<string, string> = {
  c_language: "C 语言程序设计",
  cpp: "C++ 程序设计",
  python: "Python 程序设计",
  java: "Java 程序设计",
  data_structures: "数据结构",
  algorithms: "算法设计与分析",
  database: "数据库原理 / SQL",
  computer_networks: "计算机网络",
  operating_systems: "操作系统",
  computer_organization: "计算机组成原理",
  web_frontend: "Web 前端开发",
  web_backend: "Web 后端开发",
  software_engineering: "软件工程",
  ai_fundamentals: "人工智能基础",
  machine_learning: "机器学习",
  big_data: "大数据技术",
};

const fileKindMap: Record<FileKind, string> = {
  quiz: "课堂测验",
  submission: "编程提交",
  interaction: "课堂互动",
  transcript: "课堂讲稿",
  ppt_timeline: "PPT 时间轴",
};

const errorLabelMap: Record<string, string> = {
  SegmentationFault: "内存访问错误",
  SyntaxError: "语法错误",
  InfiniteLoop: "死循环",
  OffByOne: "循环边界差一",
  StateUpdate: "状态更新错误",
  BoundaryCondition: "边界条件错误",
  IndexError: "下标越界",
  ArrayIndexOutOfBounds: "数组越界",
  NullPointer: "空指针错误",
  NullPointerException: "空指针错误",
  TypeError: "类型错误",
  NameError: "变量名错误",
  ValueError: "数值格式错误",
  KeyError: "键值不存在",
  ZeroDivisionError: "除零错误",
  StackOverflow: "递归过深",
  StackOverflowError: "递归过深",
  Timeout: "运行超时",
  TLE: "运行超时",
  WrongAnswer: "答案错误",
  WA: "答案错误",
  RuntimeError: "运行错误",
  RE: "运行错误",
  CompileError: "编译错误",
  CompilationError: "编译错误",
  CE: "编译错误",
  MemoryLimitExceeded: "内存超限",
  MLE: "内存超限",
  LogicError: "逻辑错误",
  ScopeError: "变量作用域错误",
  QueueBoundary: "循环队列边界错误",
  BoundaryUpdate: "边界更新错误",
  MissingBaseCase: "缺少递归终止条件",
  VirtualDispatch: "虚函数调用错误",
  JoinCondition: "数据库连接条件错误",
  AsyncOrder: "异步执行顺序错误",
  ConcurrentModification: "并发修改错误",
  RaceCondition: "竞态条件错误",
  SequenceMismatch: "序列号不匹配",
  IsolationViolation: "事务隔离异常",
  DependencyInversion: "依赖倒置问题",
  HeuristicError: "启发函数错误",
  Overfitting: "模型过拟合",
  EffectDependency: "副作用依赖错误",
  SignatureMismatch: "数字签名不匹配",
  InterruptConflict: "中断冲突",
  unknown: "未知错误",
  wrong_answer: "答案错误",
};

export function formatCourseType(courseType: string): string {
  return courseTypeMap[courseType] ?? courseType;
}

export function formatFileKind(fileKind: FileKind): string {
  return fileKindMap[fileKind] ?? fileKind;
}

export function formatErrorLabel(label: string): string {
  return errorLabelMap[label] ?? label;
}

export function formatErrorText(text: string): string {
  return Object.entries(errorLabelMap).reduce(
    (result, [code, label]) => result.replace(new RegExp(`\\b${code}\\b`, "g"), label),
    text,
  );
}
