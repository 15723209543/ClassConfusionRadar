/**
 * 本文件的作用是：读取 CSV、XLSX 文件并完成表头识别、字段映射和标准化。
 */
import type { FileKind } from "../../types/api";

export type TabularValue = string | number | boolean | null;

export interface ParsedTable {
  headers: string[];
  rows: Array<Record<string, TabularValue>>;
}

export interface MappingField {
  key: string;
  label: string;
  required: boolean;
  aliases: string[];
  autoOptions?: Array<{ label: string; value: string }>;
}

export const FIELD_SPECS: Record<FileKind, MappingField[]> = {
  quiz: [
    { key: "student_code", label: "学生编号", required: true, aliases: ["student_code", "student_id", "学号", "学生编号", "学生id", "编号"] , autoOptions: [{ label: "按行生成学生编号", value: "__row_student__" }]},
    { key: "student_name", label: "学生姓名", required: false, aliases: ["student_name", "name", "姓名", "学生姓名"] },
    { key: "question_code", label: "题目编号", required: true, aliases: ["question_code", "question_id", "题号", "题目编号", "题目", "question"], autoOptions: [{ label: "按行生成题目编号", value: "__row_question__" }] },
    { key: "score", label: "得分", required: true, aliases: ["score", "points", "得分", "分数", "成绩"], autoOptions: [{ label: "根据是否正确生成 0/1", value: "__score_from_correct__" }] },
    { key: "is_correct", label: "是否正确", required: true, aliases: ["is_correct", "correct", "是否正确", "正误", "正确", "答题结果"], autoOptions: [{ label: "根据得分判断（>0 为正确）", value: "__correct_from_score__" }] },
    { key: "event_minute", label: "发生时间（分钟）", required: true, aliases: ["event_minute", "minute", "时间", "分钟", "时间点", "发生时间", "timestamp"], autoOptions: [{ label: "按记录顺序生成分钟", value: "__row_minute__" }] },
  ],
  submission: [
    { key: "student_code", label: "学生编号", required: true, aliases: ["student_code", "student_id", "学号", "学生编号", "学生id", "编号"], autoOptions: [{ label: "按行生成学生编号", value: "__row_student__" }] },
    { key: "student_name", label: "学生姓名", required: false, aliases: ["student_name", "name", "姓名", "学生姓名"] },
    { key: "task_name", label: "任务/题目", required: true, aliases: ["task_name", "task", "problem", "题目", "任务", "题目名称", "作业"], autoOptions: [{ label: "统一填为“课堂任务”", value: "__default_task__" }] },
    { key: "language", label: "编程语言", required: true, aliases: ["language", "lang", "语言", "编程语言"], autoOptions: [{ label: "统一填为“unknown”", value: "__default_language__" }] },
    { key: "result_status", label: "运行/判题结果", required: true, aliases: ["result_status", "status", "result", "verdict", "结果", "状态", "判题结果", "运行结果"], autoOptions: [{ label: "根据错误信息自动判断", value: "__result_from_error__" }] },
    { key: "error_type", label: "错误类型", required: false, aliases: ["error_type", "error", "exception", "错误类型", "错误", "异常类型"] },
    { key: "error_message", label: "错误信息", required: false, aliases: ["error_message", "message", "detail", "错误信息", "异常信息", "详情"] },
    { key: "event_minute", label: "提交时间（分钟）", required: true, aliases: ["event_minute", "minute", "时间", "分钟", "提交时间", "时间点", "timestamp"], autoOptions: [{ label: "按记录顺序生成分钟", value: "__row_minute__" }] },
  ],
  interaction: [
    { key: "student_code", label: "学生编号", required: true, aliases: ["student_code", "student_id", "学号", "学生编号", "学生id", "编号"], autoOptions: [{ label: "按行生成学生编号", value: "__row_student__" }] },
    { key: "student_name", label: "学生姓名", required: false, aliases: ["student_name", "name", "姓名", "学生姓名"] },
    { key: "event_type", label: "互动类型", required: true, aliases: ["event_type", "type", "event", "互动类型", "行为", "互动", "事件"], autoOptions: [{ label: "统一填为“课堂互动”", value: "__default_interaction__" }] },
    { key: "value", label: "互动数值", required: false, aliases: ["value", "count", "次数", "数值", "数量"] },
    { key: "event_minute", label: "发生时间（分钟）", required: true, aliases: ["event_minute", "minute", "时间", "分钟", "时间点", "发生时间", "timestamp"], autoOptions: [{ label: "按记录顺序生成分钟", value: "__row_minute__" }] },
  ],
  transcript: [
    { key: "start_minute", label: "开始时间", required: true, aliases: ["start_minute", "start", "start_time", "开始时间", "起始时间", "时间"], autoOptions: [{ label: "按记录顺序生成开始时间", value: "__row_start__" }] },
    { key: "end_minute", label: "结束时间", required: true, aliases: ["end_minute", "end", "end_time", "结束时间", "终止时间"], autoOptions: [{ label: "开始时间 + 1 分钟", value: "__end_from_start__" }] },
    { key: "text", label: "讲稿文本", required: true, aliases: ["text", "content", "transcript", "文本", "内容", "讲稿", "讲解内容"] },
    { key: "speaker", label: "讲述者", required: false, aliases: ["speaker", "teacher", "讲述者", "教师", "发言人"] },
  ],
  ppt_timeline: [
    { key: "slide_index", label: "PPT 页码", required: true, aliases: ["slide_index", "slide", "page", "index", "页码", "页数", "页面"], autoOptions: [{ label: "按行生成页码", value: "__row_slide__" }] },
    { key: "start_minute", label: "开始时间", required: true, aliases: ["start_minute", "start", "start_time", "开始时间", "起始时间", "时间"], autoOptions: [{ label: "按记录顺序生成开始时间", value: "__row_start__" }] },
    { key: "end_minute", label: "结束时间", required: true, aliases: ["end_minute", "end", "end_time", "结束时间", "终止时间"], autoOptions: [{ label: "开始时间 + 1 分钟", value: "__end_from_start__" }] },
    { key: "slide_title", label: "页面标题", required: false, aliases: ["slide_title", "title", "页面标题", "标题", "PPT标题"] },
  ],
};

function normalizeHeader(value: string): string {
  return value.trim().toLowerCase().replace(/[\s_\-（）()【】\[\]]+/g, "");
}

export function suggestMappings(kind: FileKind, headers: string[]): Record<string, string> {
  const mapping: Record<string, string> = {};
  const normalized = headers.map((header) => ({ header, normalized: normalizeHeader(header) }));

  FIELD_SPECS[kind].forEach((field) => {
    const aliases = field.aliases.map(normalizeHeader);
    const exact = normalized.find((item) => aliases.includes(item.normalized));
    if (exact) {
      mapping[field.key] = exact.header;
      return;
    }
    const fuzzy = normalized.find((item) => aliases.some((alias) => item.normalized.includes(alias) || alias.includes(item.normalized)));
    if (fuzzy) {
      mapping[field.key] = fuzzy.header;
      return;
    }
    if (field.autoOptions?.length) {
      mapping[field.key] = field.autoOptions[0].value;
    }
  });

  // 优先让“得分”和“是否正确”互相推导，避免两个字段都被自动生成。
  if (kind === "quiz") {
    const scoreMapped = mapping.score && !mapping.score.startsWith("__");
    const correctMapped = mapping.is_correct && !mapping.is_correct.startsWith("__");
    if (scoreMapped && !correctMapped) mapping.is_correct = "__correct_from_score__";
    if (!scoreMapped && correctMapped) mapping.score = "__score_from_correct__";
  }
  return mapping;
}

export function inferKindFromHeaders(headers: string[]): FileKind | null {
  const kinds = Object.keys(FIELD_SPECS) as FileKind[];
  const scores = kinds.map((kind) => {
    const mapping = suggestMappings(kind, headers);
    const directCount = FIELD_SPECS[kind].filter((field) => {
      const value = mapping[field.key];
      return value && !value.startsWith("__");
    }).length;
    return { kind, directCount };
  });
  scores.sort((a, b) => b.directCount - a.directCount);
  if (!scores[0] || scores[0].directCount < 2 || scores[0].directCount === scores[1]?.directCount) return null;
  return scores[0].kind;
}

function parseCsvText(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === '"' && text[index + 1] === '"') {
        cell += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        cell += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(cell);
      cell = "";
    } else if (char === "\n") {
      row.push(cell.replace(/\r$/, ""));
      if (row.some((value) => value.trim() !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  row.push(cell.replace(/\r$/, ""));
  if (row.some((value) => value.trim() !== "")) rows.push(row);
  return rows;
}

function gridToParsedTable(grid: string[][]): ParsedTable {
  if (!grid.length) return { headers: [], rows: [] };
  const rawHeaders = grid[0].map((value, index) => value.trim() || `未命名列_${index + 1}`);
  const seen = new Map<string, number>();
  const headers = rawHeaders.map((header) => {
    const count = seen.get(header) ?? 0;
    seen.set(header, count + 1);
    return count === 0 ? header : `${header}_${count + 1}`;
  });
  const rows = grid.slice(1).map((values) => {
    const row: Record<string, TabularValue> = {};
    headers.forEach((header, index) => {
      row[header] = values[index] ?? "";
    });
    return row;
  }).filter((row) => Object.values(row).some((value) => String(value ?? "").trim() !== ""));
  return { headers, rows };
}

function findEndOfCentralDirectory(bytes: Uint8Array): number {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  for (let offset = bytes.length - 22; offset >= Math.max(0, bytes.length - 65557); offset -= 1) {
    if (view.getUint32(offset, true) === 0x06054b50) return offset;
  }
  throw new Error("无法读取 XLSX：未找到 ZIP 目录信息。");
}

async function inflateRaw(data: Uint8Array): Promise<Uint8Array> {
  if (!("DecompressionStream" in window)) {
    throw new Error("当前浏览器不支持直接解析 XLSX，请另存为 CSV 后上传。 ");
  }
  const copy = new Uint8Array(data.byteLength);
  copy.set(data);
  const stream = new Blob([copy.buffer]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function readZipEntries(bytes: Uint8Array): Promise<Map<string, Uint8Array>> {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const eocd = findEndOfCentralDirectory(bytes);
  const totalEntries = view.getUint16(eocd + 10, true);
  let offset = view.getUint32(eocd + 16, true);
  const decoder = new TextDecoder("utf-8");
  const entries = new Map<string, Uint8Array>();

  for (let index = 0; index < totalEntries; index += 1) {
    if (view.getUint32(offset, true) !== 0x02014b50) break;
    const method = view.getUint16(offset + 10, true);
    const compressedSize = view.getUint32(offset + 20, true);
    const fileNameLength = view.getUint16(offset + 28, true);
    const extraLength = view.getUint16(offset + 30, true);
    const commentLength = view.getUint16(offset + 32, true);
    const localOffset = view.getUint32(offset + 42, true);
    const fileName = decoder.decode(bytes.slice(offset + 46, offset + 46 + fileNameLength));

    if (view.getUint32(localOffset, true) !== 0x04034b50) throw new Error("XLSX ZIP 数据损坏。");
    const localNameLength = view.getUint16(localOffset + 26, true);
    const localExtraLength = view.getUint16(localOffset + 28, true);
    const dataStart = localOffset + 30 + localNameLength + localExtraLength;
    const compressed = bytes.slice(dataStart, dataStart + compressedSize);
    if (method === 0) entries.set(fileName, compressed);
    else if (method === 8) entries.set(fileName, await inflateRaw(compressed));

    offset += 46 + fileNameLength + extraLength + commentLength;
  }
  return entries;
}

function xmlText(bytes: Uint8Array): Document {
  const text = new TextDecoder("utf-8").decode(bytes);
  return new DOMParser().parseFromString(text, "application/xml");
}

function getElements(parent: Document | Element, localName: string): Element[] {
  return Array.from(parent.getElementsByTagNameNS("*", localName));
}

function columnIndexFromRef(ref: string): number {
  const letters = (ref.match(/[A-Z]+/i)?.[0] ?? "A").toUpperCase();
  let value = 0;
  for (const letter of letters) value = value * 26 + (letter.charCodeAt(0) - 64);
  return Math.max(0, value - 1);
}

function xlsxSheetToGrid(entries: Map<string, Uint8Array>): string[][] {
  const sheetBytes = entries.get("xl/worksheets/sheet1.xml");
  if (!sheetBytes) throw new Error("XLSX 中没有找到第一个工作表。");

  const sharedStringsBytes = entries.get("xl/sharedStrings.xml");
  const sharedStrings = sharedStringsBytes
    ? getElements(xmlText(sharedStringsBytes), "si").map((item) => getElements(item, "t").map((node) => node.textContent ?? "").join(""))
    : [];
  const sheet = xmlText(sheetBytes);
  const rows: string[][] = [];

  getElements(sheet, "row").forEach((rowNode) => {
    const row: string[] = [];
    getElements(rowNode, "c").forEach((cell) => {
      const ref = cell.getAttribute("r") ?? "A1";
      const type = cell.getAttribute("t") ?? "";
      const valueNode = getElements(cell, "v")[0];
      let value = valueNode?.textContent ?? "";
      if (type === "s") value = sharedStrings[Number(value)] ?? value;
      if (type === "inlineStr") value = getElements(cell, "t").map((node) => node.textContent ?? "").join("");
      if (type === "b") value = value === "1" ? "true" : "false";
      row[columnIndexFromRef(ref)] = value;
    });
    rows.push(row.map((value) => value ?? ""));
  });
  return rows;
}

export async function parseTabularFile(file: File): Promise<ParsedTable> {
  const suffix = file.name.split(".").pop()?.toLowerCase();
  if (suffix === "csv") {
    const bytes = new Uint8Array(await file.arrayBuffer());
    let text = new TextDecoder("utf-8", { fatal: false }).decode(bytes);
    if (text.includes("�")) {
      try {
        text = new TextDecoder("gb18030", { fatal: false }).decode(bytes);
      } catch {
        // 保留 UTF-8 解码结果，后面仍可人工映射。
      }
    }
    return gridToParsedTable(parseCsvText(text.replace(/^\uFEFF/, "")));
  }
  if (suffix === "xlsx" || suffix === "xlsm") {
    const entries = await readZipEntries(new Uint8Array(await file.arrayBuffer()));
    return gridToParsedTable(xlsxSheetToGrid(entries));
  }
  throw new Error("仅支持 CSV、XLSX 或 XLSM 文件。");
}

function toMinute(value: TabularValue, fallback: number): string {
  const text = String(value ?? "").trim();
  if (!text) return String(fallback);
  if (/^\d+(?:\.\d+)?$/.test(text)) return text;
  const time = text.match(/^(\d{1,2}):([0-5]?\d)(?::([0-5]?\d))?$/);
  if (time) {
    const hour = Number(time[1]);
    const minute = Number(time[2]);
    const second = Number(time[3] ?? 0);
    return String(Number((hour * 60 + minute + second / 60).toFixed(3)));
  }
  return String(fallback);
}

function truthy(value: TabularValue): boolean {
  const text = String(value ?? "").trim().toLowerCase();
  return ["1", "true", "yes", "y", "是", "正确", "通过", "pass", "accepted", "ac"].includes(text);
}

function mappedValue(
  kind: FileKind,
  fieldKey: string,
  source: string,
  row: Record<string, TabularValue>,
  rowIndex: number,
  mapping: Record<string, string>,
): string {
  if (!source) return "";
  if (!source.startsWith("__")) {
    const raw = row[source] ?? "";
    if (fieldKey.endsWith("minute")) return toMinute(raw, rowIndex + 1);
    return String(raw ?? "").trim();
  }
  switch (source) {
    case "__row_student__": return `S${String(rowIndex + 1).padStart(3, "0")}`;
    case "__row_question__": return `Q${String(rowIndex + 1).padStart(3, "0")}`;
    case "__row_minute__": return String(rowIndex + 1);
    case "__row_start__": return String(rowIndex);
    case "__row_slide__": return String(rowIndex + 1);
    case "__default_task__": return "课堂任务";
    case "__default_language__": return "unknown";
    case "__default_interaction__": return "课堂互动";
    case "__score_from_correct__": {
      const sourceKey = mapping.is_correct;
      return sourceKey && !sourceKey.startsWith("__") && truthy(row[sourceKey]) ? "1" : "0";
    }
    case "__correct_from_score__": {
      const sourceKey = mapping.score;
      const score = sourceKey && !sourceKey.startsWith("__") ? Number(row[sourceKey] ?? 0) : 0;
      return score > 0 ? "true" : "false";
    }
    case "__result_from_error__": {
      const errorType = mapping.error_type && !mapping.error_type.startsWith("__") ? row[mapping.error_type] : "";
      const errorMessage = mapping.error_message && !mapping.error_message.startsWith("__") ? row[mapping.error_message] : "";
      return String(errorType ?? "").trim() || String(errorMessage ?? "").trim() ? "failed" : "success";
    }
    case "__end_from_start__": {
      const startSource = mapping.start_minute;
      const start = startSource ? Number(mappedValue(kind, "start_minute", startSource, row, rowIndex, mapping)) : rowIndex;
      return String(Number((start + 1).toFixed(3)));
    }
    default: return "";
  }
}

export function normalizeRowsForUpload(
  kind: FileKind,
  table: ParsedTable,
  mapping: Record<string, string>,
): string {
  const fields = FIELD_SPECS[kind];
  const headers = fields.map((field) => field.key);
  const rows = table.rows.map((row, rowIndex) =>
    headers.map((fieldKey) => mappedValue(kind, fieldKey, mapping[fieldKey] ?? "", row, rowIndex, mapping)),
  );
  return serializeCsv([headers, ...rows]);
}

function escapeCsv(value: string): string {
  if (/[",\r\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

function serializeCsv(rows: string[][]): string {
  return `\uFEFF${rows.map((row) => row.map(escapeCsv).join(",")).join("\r\n")}\r\n`;
}
