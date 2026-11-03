/**
 * 本文件的作用是：声明前后端交互使用的 TypeScript 数据类型。
 */
export type SessionStatus = "draft" | "ready" | "analyzed";
export type FileKind = "quiz" | "submission" | "interaction" | "transcript" | "ppt_timeline";
export type ParseStatus = "pending" | "processing" | "success" | "failed";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type SuggestionStatus = "processing" | "ready" | "failed";

export interface UploadedFileItem {
  id: number;
  session_id: number;
  file_kind: FileKind;
  original_name: string;
  storage_path: string;
  parse_status: ParseStatus;
  row_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetImportResult {
  uploaded_files: UploadedFileItem[];
  knowledge_points_created: number;
  skipped_files: string[];
  manifest_found: boolean;
}

export interface KnowledgePointItem {
  id: number;
  session_id: number;
  name: string;
  topic_area: string | null;
  description: string | null;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface TeachingSegmentItem {
  id: number;
  session_id: number;
  knowledge_point_id: number | null;
  title: string;
  start_minute: number;
  end_minute: number;
  display_order: number;
  teacher_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface AutoSegmentSourceInfo {
  transcript_file_id: number;
  transcript_filename: string;
  ppt_timeline_file_id: number;
  ppt_timeline_filename: string;
}

export interface AutoSegmentBuildResult {
  created_count: number;
  replaced_existing: boolean;
  transcript_chunk_count: number;
  slide_window_count: number;
  source_files: AutoSegmentSourceInfo;
  message: string;
  segments: TeachingSegmentItem[];
}

export interface SessionSummary {
  id: number;
  title: string;
  course_type: string;
  class_date: string;
  duration_minutes: number;
  status: SessionStatus;
  notes: string | null;
  segment_count: number;
  knowledge_point_count: number;
  upload_count: number;
  high_risk_count: number;
  created_at: string;
  updated_at: string;
}

export interface SessionDetail extends SessionSummary {
  latest_analysis_run_id: number | null;
  uploaded_files: UploadedFileItem[];
  knowledge_points: KnowledgePointItem[];
  segments: TeachingSegmentItem[];
}

export interface AnalysisRun {
  id: number;
  session_id: number;
  status: "pending" | "completed" | "failed";
  started_at: string | null;
  finished_at: string | null;
}

export interface HeatmapCell {
  segment_id: number;
  segment_title: string;
  signal_key: string;
  signal_label: string;
  value: number;
  is_available?: boolean;
}

export interface ErrorStat {
  label: string;
  count: number;
}

export interface ScoringRuleItem {
  key: string;
  label: string;
  weight_percent: number;
  description: string;
}

export interface SignalBreakdownItem {
  key: string;
  label: string;
  weight_percent: number;
  effective_weight_percent?: number;
  raw_value: number;
  value_percent: number;
  contribution_score: number;
  samples: number;
  is_available?: boolean;
  description: string;
  evidence_summary: string;
}

export interface RiskSegmentItem {
  segment_score_id: number;
  segment_id: number;
  title: string;
  knowledge_point_name: string | null;
  start_minute: number;
  end_minute: number;
  confusion_score: number;
  risk_level: RiskLevel;
  data_coverage_percent?: number;
  confidence_level?: string;
  confidence_label?: string;
  primary_signal_label: string | null;
  primary_signal_value_percent: number | null;
  primary_signal_contribution_score: number | null;
  main_error_summary: string;
  overall_explanation: string;
}

export interface AnalyticsOverview {
  has_analysis: boolean;
  latest_run_id: number | null;
  generated_at: string | null;
  score_formula: string;
  scoring_rules: ScoringRuleItem[];
  summary: {
    average_score: number;
    high_risk_count: number;
    critical_count: number;
    total_segments: number;
    average_data_coverage_percent?: number;
    low_confidence_count?: number;
  };
  heatmap_cells: HeatmapCell[];
  top_errors: ErrorStat[];
  high_risk_segments: RiskSegmentItem[];
}

export interface SegmentAnalyticsDetail {
  segment_score_id: number;
  segment_id: number;
  session_id: number;
  title: string;
  knowledge_point_name: string | null;
  start_minute: number;
  end_minute: number;
  teacher_notes: string | null;
  confusion_score: number;
  risk_level: RiskLevel;
  data_coverage_percent?: number;
  confidence_level?: string;
  confidence_label?: string;
  score_formula: string;
  signal_breakdown: SignalBreakdownItem[];
  error_summary: ErrorStat[];
  main_error_summary: string;
  overall_explanation: string;
  generated_at: string | null;
}

export interface EnhanceAnalysisRequest {
  force_refresh?: boolean;
  allow_web_search?: boolean;
  include_memory?: boolean;
}

export interface AnalysisCitation {
  title: string;
  url: string | null;
  source_type: string;
  excerpt: string;
}

export interface TopSegmentInsight {
  segment_score_id: number;
  segment_id: number | null;
  title: string;
  why_high_risk: string;
  teacher_focus: string;
}

export interface EnhancedSessionAnalysis {
  id: number;
  analysis_run_id: number;
  status: "processing" | "ready" | "failed";
  model_name: string;
  generation_mode: "offline_rule" | "ai" | string;
  generation_mode_label: string;
  prompt_version: string;
  summary: string | null;
  teacher_takeaways: string[];
  top_segment_insights: TopSegmentInsight[];
  citations: AnalysisCitation[];
  memory_notes: string[];
  generated_at: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface EnhancedSegmentAnalysis {
  id: number;
  segment_score_id: number;
  status: "processing" | "ready" | "failed";
  model_name: string;
  generation_mode: "offline_rule" | "ai" | string;
  generation_mode_label: string;
  prompt_version: string;
  diagnosis: string | null;
  evidence_story: string | null;
  teacher_focus: string[];
  recommended_checks: string[];
  citations: AnalysisCitation[];
  memory_notes: string[];
  generated_at: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReteachingSuggestion {
  id: number;
  segment_score_id: number;
  status: SuggestionStatus;
  model_name: string;
  generation_mode: "offline_rule" | "ai" | string;
  generation_mode_label: string;
  prompt_version: string;
  structured_content: {
    diagnosis: string;
    reteach_script: string[];
    board_plan: string[];
    micro_exercises: string[];
    followup_task: string;
  } | null;
  suggestion_markdown: string | null;
  failure_reason: string | null;
  generated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReteachingInterventionCreate {
  status?: "planned" | "executed" | "verified";
  plan_text?: string | null;
  outcome_summary?: string | null;
  followup_score_before?: number | null;
  followup_score_after?: number | null;
}

export interface ReteachingInterventionRead {
  id: number;
  segment_score_id: number;
  status: string;
  plan_text: string | null;
  outcome_summary: string | null;
  followup_score_before: number | null;
  followup_score_after: number | null;
  executed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiMessage {
  message: string;
}
