import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  App, Button, Card, Col, Empty, Form, Input, Modal, Popconfirm, Progress, Row, Select,
  Space, Table, Tabs, Tag,
} from 'antd';
import { CheckOutlined, FileSearchOutlined, PlusOutlined } from '@ant-design/icons';
import {
  createRequirement, deleteRequirement, getReqSummary, listDocuments, listProjects,
  listRequirements, updateRequirement,
} from '../api/modules';
import type { DocumentFile, Importance, ReqCategory, ReqSummaryItem, Requirement, TenderProject } from '../api/types';
import { PageHeader } from '../components/PageHeader';
import { CATEGORY, IMPORTANCE, ImportanceTag, REQ_STATUS_COLOR } from '../components/statusTags';

const EXTRACTION_LABEL: Record<string, string> = { manual: '人工录入', rule: '规则提取', ai: 'AI 提取' };
const VERIFY_COLOR: Record<string, string> = { pending: 'default', confirmed: 'success', rejected: 'error' };
const VERIFY_LABEL: Record<string, string> = { pending: '待核验', confirmed: '已确认', rejected: '已驳回' };

export default function Requirements() {
  const { message } = App.useApp();
  const [rows, setRows] = useState<Requirement[]>([]);
  const [summary, setSummary] = useState<Record<string, ReqSummaryItem> | null>(null);
  const [projects, setProjects] = useState<TenderProject[]>([]);
  const [documents, setDocuments] = useState<DocumentFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [projectFilter, setProjectFilter] = useState<number | null>(null);
  const [tab, setTab] = useState<ReqCategory>('technical');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Requirement | null>(null);
  const [form] = Form.useForm();

  const load = useCallback(() => {
    setLoading(true);
    listRequirements({ project_id: projectFilter ?? undefined, category: tab })
      .then(setRows)
      .finally(() => setLoading(false));
    getReqSummary().then(setSummary).catch(() => undefined);
  }, [projectFilter, tab]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    listProjects().then(setProjects).catch(() => undefined);
    listDocuments().then(setDocuments).catch(() => undefined);
  }, []);

  const projectName = useMemo(
    () => new Map(projects.map((p) => [p.id, p.name])),
    [projects],
  );

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      importance: 'medium', status: '未开始', project_id: projectFilter ?? undefined,
      extraction_method: 'manual', verification_status: 'pending',
    });
    setModalOpen(true);
  };

  const openEdit = (r: Requirement) => {
    setEditing(r);
    form.setFieldsValue({
      project_id: r.project_id, name: r.name, content: r.content, source_text: r.source_text,
      page_no: r.page_no, importance: r.importance, status: r.status,
      document_id: r.document_id ?? undefined, page_number: r.page_number ?? undefined,
      chapter_title: r.chapter_title, section_number: r.section_number,
      original_text: r.original_text, extraction_method: r.extraction_method,
      verification_status: r.verification_status,
    });
    setModalOpen(true);
  };

  const submit = async () => {
    const v = await form.validateFields();
    const payload = {
      ...v,
      document_id: v.document_id ?? null,
      page_number: v.page_number !== undefined && v.page_number !== ("" as unknown)
        ? Number(v.page_number) : null,
    };
    try {
      if (editing) await updateRequirement(editing.id, payload);
      else await createRequirement({ ...payload, category: tab });
      message.success(editing ? '要求已更新' : '要求已新增');
      setModalOpen(false);
      load();
    } catch (e) { message.error((e as Error).message); }
  };

  const toggleVerify = async (r: Requirement) => {
    const next = r.verification_status === 'confirmed' ? 'pending' : 'confirmed';
    try { await updateRequirement(r.id, { verification_status: next }); load(); }
    catch { message.error('操作失败'); }
  };

  const columns = [
    {
      title: '要求名称', dataIndex: 'name', width: 200, ellipsis: true,
      render: (v: string, r: Requirement) => (
        <Space size={6}>
          <ImportanceTag value={r.importance} />
          <span style={{ fontWeight: 600, color: '#22314c' }}>{v}</span>
        </Space>
      ),
    },
    {
      title: '具体内容', dataIndex: 'content', ellipsis: true,
      render: (v: string) => <span style={{ fontSize: 13, color: '#5a6b84' }}>{v}</span>,
    },
    {
      title: '原始文件', dataIndex: 'document_name', width: 170, ellipsis: true,
      render: (v: string | null, r: Requirement) => v ? (
        <Space size={4}>
          <FileSearchOutlined style={{ color: '#1668dc' }} />
          <span>{v}{r.page_number ? ` · P${r.page_number}` : ''}</span>
        </Space>
      ) : <span style={{ color: '#b3bdcf' }}>未关联</span>,
    },
    { title: '原文出处', dataIndex: 'source_text', width: 170, ellipsis: true, render: (v: string) => v || '—' },
    {
      title: '页码', dataIndex: 'page_number', width: 80,
      render: (v: number | null, r: Requirement) => v ?? (r.page_no || '—'),
    },
    {
      title: '重要程度', dataIndex: 'importance', width: 90,
      render: (v: Importance) => {
        const c = IMPORTANCE[v] ?? IMPORTANCE.medium;
        return <Tag color={c.color}>{c.label}</Tag>;
      },
    },
    {
      title: '完成状态', dataIndex: 'status', width: 100,
      render: (v: string) => <Tag color={REQ_STATUS_COLOR[v]}>{v}</Tag>,
    },
    {
      title: '核验状态', dataIndex: 'verification_status', width: 100,
      render: (v: Requirement['verification_status'], r: Requirement) => (
        <Space size={4}>
          <Tag color={VERIFY_COLOR[v]}>{VERIFY_LABEL[v]}</Tag>
          {v === 'confirmed' && (
            <Button size="small" type="text" icon={<CheckOutlined />} onClick={() => toggleVerify(r)} />
          )}
          {v !== 'confirmed' && (
            <Button size="small" onClick={() => toggleVerify(r)}>确认</Button>
          )}
        </Space>
      ),
    },
    {
      title: '操作', key: 'op', width: 120,
      render: (_: unknown, r: Requirement) => (
        <Space size={4}>
          <Button type="link" size="small" onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除该要求？" onConfirm={async () => {
            try { await deleteRequirement(r.id); message.success('已删除'); load(); }
            catch { message.error('删除失败'); }
          }}>
            <Button type="link" size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const summaryCards = (['technical', 'business', 'credit'] as const).map((cat) => {
    const s = summary?.[cat];
    const pct = s && s.total ? Math.round((s.done / s.total) * 100) : 0;
    return (
      <Col xs={24} sm={8} key={cat}>
        <Card size="small">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <Space>
              <Tag color={CATEGORY[cat].color}>{CATEGORY[cat].label}</Tag>
              <span style={{ fontSize: 12, color: '#93a1b5' }}>{s?.total ?? 0} 项</span>
            </Space>
            <span style={{ fontSize: 13, color: '#5a6b84' }}>
              完成 {s?.done ?? 0} · 已确认 {s?.confirmed ?? 0}
            </span>
          </div>
          <Progress percent={pct} size="small"
            strokeColor={cat === 'technical' ? '#1668dc' : cat === 'business' ? '#d48806' : '#389e0d'} />
          <div style={{ fontSize: 12, color: '#93a1b5', marginTop: 6 }}>{CATEGORY[cat].desc}</div>
        </Card>
      </Col>
    );
  });

  const tabItems = (['technical', 'business', 'credit'] as const).map((cat) => ({
    key: cat,
    label: (
      <span>
        {CATEGORY[cat].label}
        <Tag style={{ marginInlineStart: 6 }} color={CATEGORY[cat].color}>
          {projectFilter
            ? rows.filter((r) => r.category === cat).length
            : summary?.[cat]?.total ?? '—'}
        </Tag>
      </span>
    ),
  }));

  return (
    <div>
      <PageHeader
        title="投标要求管理"
        subtitle="技术标 / 商务标 / 资信标三类要求独立管理，逐项记录原文出处、页码、重要程度、完成与人工确认状态"
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新增{CATEGORY[tab].label}要求
        </Button>}
      />
      <Row gutter={16} style={{ marginBottom: 16 }}>{summaryCards}</Row>

      <Card styles={{ body: { paddingBottom: 8 } }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
          <Tabs activeKey={tab} onChange={(k) => setTab(k as ReqCategory)} items={tabItems} style={{ flex: 1 }} />
          <Select
            style={{ width: 280 }} allowClear placeholder="按项目筛选（全部项目）"
            showSearch optionFilterProp="label"
            value={projectFilter ?? undefined}
            onChange={(v) => setProjectFilter(v ?? null)}
            options={projects.map((p) => ({ value: p.id, label: `${p.name}（${p.code}）` }))}
          />
        </div>
        <Table
          rowKey="id" columns={columns} dataSource={rows} loading={loading}
          locale={{ emptyText: <Empty description={`暂无${CATEGORY[tab].label}要求`} /> }}
          pagination={{ pageSize: 8, showTotal: (t) => `共 ${t} 条` }}
          expandable={{
            rowExpandable: (r) => !!(r.content || r.remark || r.original_text),
            expandedRowRender: (r) => (
              <div style={{ padding: '4px 0', fontSize: 13, lineHeight: 1.9 }}>
                <div><b style={{ color: '#7a8aa3' }}>具体内容：</b>{r.content || '—'}</div>
                <div><b style={{ color: '#7a8aa3' }}>所属项目：</b>{projectName.get(r.project_id) ?? r.project_id}</div>
                {r.document_name && (
                  <div>
                    <b style={{ color: '#7a8aa3' }}>原始文件：</b>
                    <a href={`/api/documents/${r.document_id}/download`} target="_blank" rel="noreferrer">
                      {r.document_name}
                    </a>
                    {r.page_number ? `（第 ${r.page_number} 页）` : ''}
                    {r.chapter_title ? ` · ${r.chapter_title}` : ''}
                    {r.section_number ? ` ${r.section_number}` : ''}
                    <Tag style={{ marginInlineStart: 8 }}>{EXTRACTION_LABEL[r.extraction_method] ?? r.extraction_method}</Tag>
                  </div>
                )}
                {r.original_text && (
                  <div style={{
                    background: '#f7f9fc', borderLeft: '3px solid #1668dc', padding: '6px 10px',
                    borderRadius: 4, marginTop: 4, whiteSpace: 'pre-wrap',
                  }}>
                    <b style={{ color: '#7a8aa3' }}>原始条款：</b>{r.original_text}
                  </div>
                )}
                {r.verification_status === 'confirmed' && r.verified_by && (
                  <div style={{ color: '#93a1b5', fontSize: 12 }}>
                    核验：{r.verified_by} · {r.verified_at?.slice(0, 16).replace('T', ' ')}
                  </div>
                )}
                {r.remark && <div><b style={{ color: '#7a8aa3' }}>备注：</b>{r.remark}</div>}
              </div>
            ),
          }}
        />
      </Card>

      <Modal
        title={editing ? '编辑投标要求' : `新增${CATEGORY[tab].label}要求`}
        open={modalOpen} onCancel={() => setModalOpen(false)} onOk={submit}
        okText="保存" cancelText="取消" width={620} destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="project_id" label="所属项目" rules={[{ required: true, message: '请选择项目' }]}>
            <Select placeholder="选择招标项目" showSearch optionFilterProp="label"
              options={projects.map((p) => ({ value: p.id, label: `${p.name}（${p.code}）` }))} />
          </Form.Item>
          {!editing && (
            <div style={{ marginBottom: 12, fontSize: 12.5, color: '#93a1b5' }}>
              当前新增到「{CATEGORY[tab].label}」分类（与页面顶部页签一致）
            </div>
          )}
          <Form.Item name="name" label="要求名称" rules={[{ required: true, message: '请输入要求名称' }]}>
            <Input placeholder="如：深基坑专项施工方案" />
          </Form.Item>
          <Form.Item name="content" label="具体内容">
            <Input.TextArea rows={3} placeholder="要求的具体内容描述" />
          </Form.Item>
          <Space style={{ display: 'flex' }}>
            <Form.Item name="source_text" label="原文出处" style={{ width: 300 }}>
              <Input placeholder="如：第二章 投标人须知前附表 3.2" />
            </Form.Item>
            <Form.Item name="page_no" label="页码（旧字段，兼容）" style={{ width: 160 }}>
              <Input placeholder="如 P15 / P88-102" />
            </Form.Item>
          </Space>
          <Card size="small" title="原始文件追溯（整改新增，可选）" style={{ marginBottom: 12 }}>
            <Space style={{ display: 'flex' }}>
              <Form.Item name="document_id" label="关联招标文件" style={{ width: 340 }}>
                <Select placeholder="选择原始文件（可空）" allowClear showSearch optionFilterProp="label"
                  options={documents.map((d) => ({ value: d.id, label: d.original_name }))} />
              </Form.Item>
              <Form.Item name="page_number" label="页码" style={{ width: 90 }}>
                <Input type="number" min={1} placeholder="如 15" />
              </Form.Item>
              <Form.Item name="section_number" label="条款编号" style={{ width: 120 }}>
                <Input placeholder="如 3.2.1" />
              </Form.Item>
            </Space>
            <Form.Item name="chapter_title" label="所属章节">
              <Input placeholder="如：第二章 投标人须知及前附表" />
            </Form.Item>
            <Form.Item name="original_text" label="原始文本片段">
              <Input.TextArea rows={2} placeholder="摘录招标文件中的原始条款内容，便于追溯与 AI 校对" />
            </Form.Item>
            <Space style={{ display: 'flex' }}>
              <Form.Item name="extraction_method" label="提取方式" style={{ width: 140 }}>
                <Select options={Object.entries(EXTRACTION_LABEL).map(([k, v]) => ({ value: k, label: v }))} />
              </Form.Item>
              <Form.Item name="verification_status" label="核验状态" style={{ width: 140 }}>
                <Select options={Object.entries(VERIFY_LABEL).map(([k, v]) => ({ value: k, label: v }))} />
              </Form.Item>
            </Space>
          </Card>
          <Space style={{ display: 'flex' }}>
            <Form.Item name="importance" label="重要程度" style={{ width: 140 }}>
              <Select options={Object.entries(IMPORTANCE).map(([k, v]) => ({ value: k as Importance, label: v.label }))} />
            </Form.Item>
            <Form.Item name="status" label="完成状态" style={{ width: 140 }}>
              <Select options={['未开始', '进行中', '已完成'].map((v) => ({ value: v }))} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </div>
  );
}
