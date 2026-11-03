/** 与后端 schemas.py 对应的类型定义 */

export type ReqCategory = 'technical' | 'business' | 'credit';
export type Importance = 'high' | 'medium' | 'low';

export interface TenderProject {
  id: number;
  code: string;
  name: string;
  region: string;
  project_type: string;
  tender_method: string;
  tenderer: string;
  agency: string;
  budget: number;
  publish_date: string | null;
  deadline: string | null;
  stage: string;
  participating: boolean;
  favorite: boolean;
  description: string;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Announcement {
  id: number;
  title: string;
  ann_type: string;
  project_code: string;
  source: string;
  source_url: string;
  publish_date: string | null;
  content: string;
  winner: string;
  win_amount: number;
  is_demo: boolean;
  created_at: string;
}

export interface Paged<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface ParseSection {
  title: string;
  items: string[];
}
export interface ParseResult {
  is_demo: boolean;
  note: string;
  sections: ParseSection[];
  suggested_requirements?: { category: ReqCategory; name: string; source_text: string }[];
}

export interface DocumentFile {
  id: number;
  original_name: string;
  stored_name: string;
  file_type: string;
  size: number;
  project_id: number | null;
  status: '待解析' | '解析中' | '解析完成' | '解析失败';
  parse_result: string;
  error_message: string;
  is_demo: boolean;
  uploaded_at: string;
  project_name: string | null;
}

export interface Requirement {
  id: number;
  project_id: number;
  category: ReqCategory;
  name: string;
  content: string;
  source_text: string;
  page_no: string;
  importance: Importance;
  status: string;
  confirmed: boolean;
  remark: string;
  // 整改 C1：原始文件追溯
  document_id: number | null;
  page_number: number | null;
  chapter_title: string;
  section_number: string;
  original_text: string;
  extraction_method: 'manual' | 'rule' | 'ai';
  verification_status: 'pending' | 'confirmed' | 'rejected';
  verified_at: string | null;
  verified_by: string;
  created_at: string;
  updated_at: string;
  project_name: string | null;
  document_name: string | null;
}

export interface ReqSummaryItem {
  label: string;
  total: number;
  done: number;
  in_progress: number;
  confirmed: number;
}

export interface HistoricalProject {
  id: number;
  project_name: string;
  project_code: string;
  region: string;
  project_type: string;
  tender_method: string;
  tenderer: string;
  winner: string;
  bid_amount: number;
  control_amount: number;
  participants: string[];
  bid_open_date: string | null;
  remarks: string;
  is_demo: boolean;
}

export interface BidTask {
  id: number;
  project_id: number;
  title: string;
  owner: string;
  due_date: string | null;
  status: string;
  priority: Importance;
  remark: string;
  created_at: string;
}

export interface Milestone {
  id: number;
  project_id: number;
  name: string;
  date: string | null;
  kind: string;
  description: string;
}

export interface Deliverable {
  id: number;
  project_id: number;
  name: string;
  category: string;
  version: string;
  file_path: string;
  size: number;
  uploaded_at: string;
}

export interface BidProjectRow {
  id: number;
  name: string;
  code: string;
  region: string;
  project_type: string;
  stage: string;
  deadline: string | null;
  budget: number;
  task_total: number;
  task_done: number;
  progress: number;
  milestone_count: number;
  deliverable_count: number;
}

export interface ChatMessage {
  id: number;
  session_id: number;
  role: 'user' | 'assistant';
  content: string;
  is_mock: boolean;
  created_at: string;
}

export interface ChatSession {
  id: number;
  title: string;
  context_type: string;
  context_ref: string;
  created_at: string;
  messages?: ChatMessage[];
}

export interface DashboardData {
  project_count: number;
  participating_count: number;
  favorite_count: number;
  pending_task_count: number;
  document_count: number;
  requirement_pending: number;
  announcement_count: number;
  history_count: number;
  type_distribution: { name: string; value: number }[];
  win_trend: { month: string; amount: number }[];
  recent_projects: TenderProject[];
  recent_documents: DocumentFile[];
  bid_progress: { project_id: number; name: string; deadline: string | null; total: number; done: number; progress: number }[];
  upcoming_milestones: { project_id: number; project_name: string; name: string; date: string; kind: string }[];
}

// ---- 第二阶段：文档解析 ----
export interface ParseStats {
  engine_version: string;
  parser: string;
  page_count: number;
  char_count: number;
  chapter_count: number;
  table_count: number;
  image_pages: number[];
  page_label_detected: number;
  extracted_items: Record<string, number>;
  warnings: string[];
}

export interface ParseTaskInfo {
  id: number;
  document_id?: number;
  version: number;
  status: 'running' | 'completed' | 'failed';
  engine_version: string;
  file_sha256: string;
  stats: ParseStats | null;
  warnings: string[] | null;
  error_message: string;
  started_at: string;
  finished_at: string | null;
}

export interface ParseResultItem {
  id: number;
  field_key: string;
  field_name: string;
  value: string;
  original_text: string;
  manual_value: string;
  pdf_page: number | null;
  page_label: string;
  chapter: string;
  section_no: string;
  method: string;
  source_layer: string;
  confidence: 'high' | 'medium' | 'low';
  verification_status: 'pending' | 'confirmed' | 'doubtful' | 'failed';
  verified_at: string | null;
  verified_by: string;
  is_carried: boolean;
  source_task_id: number | null;
}

export interface ParseLatestResp {
  task: ParseTaskInfo | null;
  categories: Record<string, ParseResultItem[]>;
  category_names: Record<string, string>;
}

export interface PackageImportResp {
  ok: boolean;
  package_id: string;
  source_sha256: string;
  files: { id: number; name: string; size: number; is_main: boolean; parse_supported: boolean }[];
  main_file: { id: number; name: string };
  meta: Record<string, string>;
  message: string;
}

export interface SettingRow {
  key: string;
  value: string;
  label: string;
  updated_at: string;
  has_value?: boolean;
  sensitive?: boolean;
  env_override?: string;
}

export interface SystemStatus {
  app: string;
  version: string;
  python: string;
  platform: string;
  fastapi: string;
  sqlalchemy: string;
  database: { path: string; size_kb: number; tables: Record<string, number> };
  storage: { upload_dir: string; tender_docs: number; deliverables: number; size_mb: number };
  note: string;
}
