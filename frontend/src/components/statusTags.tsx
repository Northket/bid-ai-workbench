import { Tag } from 'antd';
import type { Importance } from '../api/types';

/** 统一的状态/枚举标签映射，保证各页面风格一致 */

export const STAGE_COLOR: Record<string, string> = {
  跟踪中: 'geekblue',
  投标中: 'processing',
  已结束: 'default',
};

export const DOC_STATUS_COLOR: Record<string, string> = {
  待解析: 'default',
  解析中: 'processing',
  解析完成: 'success',
  解析失败: 'error',
};

export const TASK_STATUS_COLOR: Record<string, string> = {
  待办: 'default',
  进行中: 'processing',
  已完成: 'success',
};

export const REQ_STATUS_COLOR: Record<string, string> = {
  未开始: 'default',
  进行中: 'processing',
  已完成: 'success',
};

export const ANN_TYPE_COLOR: Record<string, string> = {
  招标公告: 'blue',
  开标公告: 'cyan',
  中标公告: 'green',
  更正公告: 'orange',
};

export const IMPORTANCE: Record<Importance, { label: string; color: string }> = {
  high: { label: '高', color: 'red' },
  medium: { label: '中', color: 'orange' },
  low: { label: '低', color: 'default' },
};

export const CATEGORY: Record<string, { label: string; color: string; desc: string }> = {
  technical: { label: '技术标', color: 'geekblue', desc: '施工组织设计、技术方案、人员机械配置等' },
  business: { label: '商务标', color: 'gold', desc: '报价、工程量清单、商务响应等' },
  credit: { label: '资信标', color: 'green', desc: '资质、业绩、财务、信用等' },
};

export function fmtAmount(wan: number | null | undefined, digits = 2): string {
  if (wan === null || wan === undefined) return '—';
  return `${wan.toLocaleString('zh-CN', { maximumFractionDigits: digits })} 万元`;
}

export function fmtSize(bytes: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function fmtDate(d: string | null | undefined): string {
  return d ? d.slice(0, 10) : '—';
}

export function ImportanceTag({ value }: { value: Importance }) {
  const conf = IMPORTANCE[value] ?? IMPORTANCE.medium;
  return <Tag color={conf.color}>{conf.label}</Tag>;
}
