/** 各模块 API 函数 */
import { http, qs } from './client';
import type {
  Announcement, BidProjectRow, BidTask, ChatSession, DashboardData, Deliverable,
  DocumentFile, HistoricalProject, Milestone, ParseResult, Paged, ReqSummaryItem,
  Requirement, SettingRow, SystemStatus, TenderProject,
} from './types';

// ---- 工作台 ----
export const getDashboard = () => http.get<DashboardData>('/api/dashboard');

// ---- 项目库 ----
export interface ProjectQuery {
  keyword?: string; region?: string; project_type?: string; stage?: string;
  favorite?: boolean; participating?: boolean;
  date_from?: string; date_to?: string;
}
export const listProjects = (q: ProjectQuery = {}) =>
  http.get<TenderProject[]>(`/api/projects${qs(q as Record<string, string | boolean | undefined>)}`);
export const getFilterOptions = () =>
  http.get<{ regions: string[]; project_types: string[]; stages: string[] }>('/api/projects/filter-options');
export const getProject = (id: number) => http.get<TenderProject>(`/api/projects/${id}`);
export const createProject = (body: Partial<TenderProject>) => http.post<TenderProject>('/api/projects', body);
export const updateProject = (id: number, body: Partial<TenderProject>) =>
  http.put<TenderProject>(`/api/projects/${id}`, body);
export const toggleFavorite = (id: number) => http.post<TenderProject>(`/api/projects/${id}/favorite`);
export const deleteProject = (id: number, permanent = false) =>
  http.del<{ ok: boolean; mode: string; message: string }>(`/api/projects/${id}${permanent ? '?permanent=true' : ''}`);
export const getDeleteImpact = (id: number) =>
  http.get<{
    project: { id: number; name: string; code: string };
    documents: number; requirements: number; tasks: number;
    milestones: number; deliverables: number; policy: string;
  }>(`/api/projects/${id}/delete-impact`);
export const restoreProject = (id: number) => http.post<TenderProject>(`/api/projects/${id}/restore`);
export const listDeletedProjects = () => http.get<TenderProject[]>('/api/projects/deleted');

// ---- 公告 ----
export interface AnnQuery {
  keyword?: string; ann_type?: string; date_from?: string; date_to?: string;
  page?: number; page_size?: number;
}
export const listAnnouncements = (q: AnnQuery = {}) =>
  http.get<Paged<Announcement>>(`/api/announcements${qs(q as Record<string, string | number | undefined>)}`);
export const getAnnStats = () =>
  http.get<{ total: number; by_type: Record<string, number>; demo_count: number }>('/api/announcements/stats');
export const createAnnouncement = (body: Partial<Announcement>) => http.post<Announcement>('/api/announcements', body);
export const deleteAnnouncement = (id: number) => http.del(`/api/announcements/${id}`);
export const fetchFromSource = () =>
  http.post<{ ok: boolean; status: string; message: string; reference_url: string }>('/api/announcements/fetch');

// ---- 文件解析 ----
export const listDocuments = (q: { project_id?: number; status?: string; keyword?: string } = {}) =>
  http.get<DocumentFile[]>(`/api/documents${qs(q as Record<string, string | number | undefined>)}`);
export const uploadDocument = (file: File, projectId?: number | null) => {
  const form = new FormData();
  form.append('file', file);
  if (projectId) form.append('project_id', String(projectId));
  return http.upload<DocumentFile>('/api/documents/upload', form);
};
export const parseDocument = (id: number) =>
  http.post<{ ok: boolean; status: string; result: ParseResult; error?: string }>(`/api/documents/${id}/parse`);
export const updateDocument = (id: number, body: { project_id: number | null }) =>
  http.put<DocumentFile>(`/api/documents/${id}`, body);
export const deleteDocument = (id: number) => http.del(`/api/documents/${id}`);

// ---- 第二阶段：真实文档解析 ----
export interface StartParseResp {
  ok: boolean; task_id: number; version: number; message: string; workbench_url?: string;
}
export const startParse = (docId: number) => http.post<StartParseResp>(`/api/parse/documents/${docId}`);
export const listParseTasks = (docId: number) =>
  http.get<import('./types').ParseTaskInfo[]>(`/api/parse/documents/${docId}/tasks`);
export const getParseTask = (taskId: number) =>
  http.get<import('./types').ParseTaskInfo>(`/api/parse/tasks/${taskId}`);
export const getLatestParse = (docId: number) =>
  http.get<import('./types').ParseLatestResp>(`/api/parse/documents/${docId}/latest`);
export const verifyParseResult = (id: number, body: { verification_status: string; manual_value?: string }) =>
  http.put<{ ok: boolean }>(`/api/parse/results/${id}`, body);
export const retryParseTask = (taskId: number) => http.post<{ ok: boolean }>(`/api/parse/tasks/${taskId}/retry`);
export const exportParseUrl = (taskId: number) => `/api/parse/tasks/${taskId}/export`;
export const resultToRequirement = (resultId: number) =>
  http.post<{ ok: boolean; message: string }>(`/api/parse/results/${resultId}/to-requirement`);
export const importPackage = (file: File, projectId?: number | null) => {
  const form = new FormData();
  form.append('file', file);
  if (projectId) form.append('project_id', String(projectId));
  return http.upload<import('./types').PackageImportResp>('/api/documents/import-package', form);
};
export const documentDownloadUrl = (docId: number) => `/api/documents/${docId}/download`;

// ---- 投标要求 ----
export const listRequirements = (q: { project_id?: number; category?: string; status?: string; keyword?: string } = {}) =>
  http.get<Requirement[]>(`/api/requirements${qs(q as Record<string, string | number | undefined>)}`);
export const getReqSummary = () => http.get<Record<string, ReqSummaryItem>>('/api/requirements/summary');
export const createRequirement = (body: Partial<Requirement>) => http.post<Requirement>('/api/requirements', body);
export const updateRequirement = (id: number, body: Partial<Requirement>) =>
  http.put<Requirement>(`/api/requirements/${id}`, body);
export const deleteRequirement = (id: number) => http.del(`/api/requirements/${id}`);

// ---- 历史项目 ----
export interface HistoryQuery {
  keyword?: string; project_type?: string; region?: string;
  date_from?: string; date_to?: string; page?: number; page_size?: number;
}
export const listHistory = (q: HistoryQuery = {}) =>
  http.get<Paged<HistoricalProject>>(`/api/history${qs(q as Record<string, string | number | undefined>)}`);
export interface HistoryStats {
  total: number;
  filters: Record<string, string>;
  amount: { valid_count: number; avg: number | null; max: number | null; min: number | null };
  control: { valid_count: number };
  discount: {
    valid_count: number; avg: number | null; max: number | null; min: number | null;
    pending_verification_count: number; pending_verification_note: string;
    invalid_count: number; invalid_note: string;
  };
  by_year: Record<string, { count: number; avg_amount: number | null }>;
  by_region: Record<string, { count: number; avg_amount: number | null }>;
  by_type: Record<string, { count: number; avg_amount: number | null }>;
  winner_ranking: { name: string; count: number; total_amount: number }[];
  participant_ranking: { name: string; count: number; total_amount: number }[];
}
export const getHistoryStats = (q: { keyword?: string; project_type?: string } = {}) =>
  http.get<HistoryStats>(`/api/history/stats${qs(q)}`);
export const createHistory = (body: Partial<HistoricalProject>) => http.post<HistoricalProject>('/api/history', body);
export const deleteHistory = (id: number) => http.del(`/api/history/${id}`);
export const importHistory = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return http.upload<{ ok: boolean; message: string; imported: number; errors: string[] }>('/api/history/import', form);
};
export const historyTemplateUrl = '/api/history/import/template';

// ---- AI ----
export const listChatSessions = () => http.get<ChatSession[]>('/api/ai/sessions');
export const getChatSession = (id: number) => http.get<ChatSession>(`/api/ai/sessions/${id}`);
export const deleteChatSession = (id: number) => http.del(`/api/ai/sessions/${id}`);
export const sendChat = (body: { session_id?: number | null; context_type: string; context_ref?: string; message: string }) =>
  http.post<{ session_id: number; reply: string; is_mock: boolean; note: string }>('/api/ai/chat', body);
export const getAiConfig = () =>
  http.get<{ provider: string; connected: boolean; message: string; has_api_key: boolean }>('/api/ai/config');

// ---- 投标管理 ----
export const listBidProjects = () => http.get<BidProjectRow[]>('/api/bids/projects');
export const getBidOverview = (projectId: number) =>
  http.get<{ project: TenderProject; tasks: BidTask[]; milestones: Milestone[]; deliverables: Deliverable[] }>(
    `/api/bids/projects/${projectId}/overview`);
export const createTask = (body: Partial<BidTask>) => http.post<BidTask>('/api/bids/tasks', body);
export const updateTask = (id: number, body: Partial<BidTask>) => http.put<BidTask>(`/api/bids/tasks/${id}`, body);
export const deleteTask = (id: number) => http.del(`/api/bids/tasks/${id}`);
export const createMilestone = (body: Partial<Milestone>) => http.post<Milestone>('/api/bids/milestones', body);
export const deleteMilestone = (id: number) => http.del(`/api/bids/milestones/${id}`);
export const uploadDeliverable = (projectId: number, category: string, version: string, file: File) => {
  const form = new FormData();
  form.append('project_id', String(projectId));
  form.append('category', category);
  form.append('version', version);
  form.append('file', file);
  return http.upload<Deliverable>('/api/bids/deliverables/upload', form);
};
export const deleteDeliverable = (id: number) => http.del(`/api/bids/deliverables/${id}`);

// ---- 设置 ----
export const getSettings = () => http.get<Record<string, SettingRow[]>>('/api/settings');
export const updateSetting = (key: string, value: string) =>
  http.put<{ ok: boolean }>(`/api/settings`, { key, value });
export const getSystemStatus = () => http.get<SystemStatus>('/api/system/status');
