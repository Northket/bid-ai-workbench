import { useCallback, useEffect, useState } from 'react';
import {
  App, Button, Card, DatePicker, Descriptions, Empty, Form, Input, Modal, Popconfirm, Select,
  Space, Table, Tag,
} from 'antd';
import { DeleteOutlined, PlusOutlined, ReloadOutlined, StarFilled, StarOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import dayjs, { type Dayjs } from 'dayjs';
import {
  createProject, deleteProject, getDeleteImpact, getFilterOptions, listDeletedProjects,
  listProjects, restoreProject, toggleFavorite, updateProject,
} from '../api/modules';
import type { TenderProject } from '../api/types';
import { PageHeader } from '../components/PageHeader';
import { STAGE_COLOR, fmtDate } from '../components/statusTags';

const { RangePicker } = DatePicker;

interface FormValues {
  name: string; code: string; region: string; project_type: string; tender_method: string;
  tenderer: string; agency: string; budget: number; range: [Dayjs, Dayjs] | null;
  stage: string; description: string;
}

const emptyForm: Partial<FormValues> = {
  name: '', code: '', region: '深圳市', project_type: '房建', tender_method: '公开招标',
  tenderer: '', agency: '', budget: 0, range: null, stage: '跟踪中', description: '',
};

export default function Projects() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [rows, setRows] = useState<TenderProject[]>([]);
  const [loading, setLoading] = useState(false);
  const [options, setOptions] = useState<{ regions: string[]; project_types: string[]; stages: string[] }>(
    { regions: [], project_types: [], stages: [] });
  const [query, setQuery] = useState({ keyword: '', region: '', project_type: '', stage: '', favorite: false });
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<TenderProject | null>(null);
  const [form] = Form.useForm();
  const [delTarget, setDelTarget] = useState<TenderProject | null>(null);
  const [delImpact, setDelImpact] = useState<Awaited<ReturnType<typeof getDeleteImpact>> | null>(null);
  const [delLoading, setDelLoading] = useState(false);
  const [recycleOpen, setRecycleOpen] = useState(false);
  const [recycleRows, setRecycleRows] = useState<TenderProject[]>([]);

  const load = useCallback(() => {
    setLoading(true);
    listProjects({
      keyword: query.keyword, region: query.region, project_type: query.project_type,
      stage: query.stage, favorite: query.favorite || undefined,
      date_from: dateRange?.[0]?.format('YYYY-MM-DD'), date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
    })
      .then(setRows)
      .catch(() => message.error('项目列表加载失败'))
      .finally(() => setLoading(false));
  }, [query, dateRange, message]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { getFilterOptions().then(setOptions).catch(() => undefined); }, []);

  const openCreate = () => { setEditing(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (p: TenderProject) => {
    setEditing(p);
    form.setFieldsValue({
      name: p.name, code: p.code, region: p.region, project_type: p.project_type,
      tender_method: p.tender_method, tenderer: p.tenderer, agency: p.agency, budget: p.budget,
      stage: p.stage, description: p.description,
      range: p.publish_date && p.deadline ? [dayjs(p.publish_date), dayjs(p.deadline)] : null,
    });
    setModalOpen(true);
  };

  const submit = async () => {
    const v = await form.validateFields();
    const body = {
      name: v.name, code: v.code, region: v.region, project_type: v.project_type,
      tender_method: v.tender_method, tenderer: v.tenderer || '', agency: v.agency || '',
      budget: v.budget ?? 0, stage: v.stage, description: v.description || '',
      publish_date: v.range?.[0]?.format('YYYY-MM-DD') ?? null,
      deadline: v.range?.[1]?.format('YYYY-MM-DD') ?? null,
    };
    try {
      if (editing) {
        await updateProject(editing.id, body);
        message.success('项目已更新');
      } else {
        const created = await createProject(body);
        message.success('项目创建成功');
        navigate(`/projects/${created.id}`);
        return;
      }
      setModalOpen(false);
      load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const onFav = async (p: TenderProject) => {
    try { await toggleFavorite(p.id); load(); } catch { message.error('操作失败'); }
  };

  /** 删除流程：先取影响范围，二次确认后软删除（进入回收站） */
  const openDelete = async (p: TenderProject) => {
    setDelTarget(p);
    setDelImpact(null);
    try { setDelImpact(await getDeleteImpact(p.id)); } catch { /* 影响范围获取失败不阻塞 */ }
  };
  const confirmDelete = async () => {
    if (!delTarget) return;
    setDelLoading(true);
    try {
      const r = await deleteProject(delTarget.id);
      message.success(r.message || '已移入回收站');
      setDelTarget(null);
      load();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setDelLoading(false);
    }
  };
  const openRecycle = async () => {
    setRecycleOpen(true);
    listDeletedProjects().then(setRecycleRows).catch(() => setRecycleRows([]));
  };
  const onRestore = async (p: TenderProject) => {
    try {
      await restoreProject(p.id);
      message.success(`项目「${p.name}」已恢复`);
      listDeletedProjects().then(setRecycleRows);
      load();
    } catch (e) { message.error((e as Error).message); }
  };

  const columns = [
    {
      title: '项目名称', dataIndex: 'name', ellipsis: true,
      render: (v: string, r: TenderProject) => (
        <Space>
          <Link to={`/projects/${r.id}`} style={{ fontWeight: 500 }}>{v}</Link>
          {r.participating && <Tag color="processing">投标中</Tag>}
        </Space>
      ),
    },
    { title: '编号', dataIndex: 'code', width: 130, ellipsis: true },
    { title: '区域', dataIndex: 'region', width: 100 },
    { title: '类型', dataIndex: 'project_type', width: 90 },
    {
      title: '预算（万元）', dataIndex: 'budget', width: 120, align: 'right' as const,
      render: (v: number) => v.toLocaleString('zh-CN', { maximumFractionDigits: 0 }),
    },
    { title: '公告日期', dataIndex: 'publish_date', width: 105, render: (v: string) => fmtDate(v) },
    {
      title: '截止日期', dataIndex: 'deadline', width: 105, render: (v: string) => {
        const d = fmtDate(v);
        if (!r_deadline_warn(v)) return d;
        return <span style={{ color: '#cf1322' }}>{d}</span>;
      },
    },
    { title: '阶段', dataIndex: 'stage', width: 90, render: (v: string) => <Tag color={STAGE_COLOR[v]}>{v}</Tag> },
    {
      title: '操作', key: 'op', width: 170,
      render: (_: unknown, r: TenderProject) => (
        <Space size={4}>
          <Button type="text" size="small" icon={r.favorite ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
            onClick={() => onFav(r)}>{r.favorite ? '已收藏' : '收藏'}</Button>
          <Button type="link" size="small" onClick={() => openEdit(r)}>编辑</Button>
          <Button type="link" size="small" danger onClick={() => openDelete(r)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="招标项目库"
        subtitle={<>共 {rows.length} 个项目 · 支持关键词检索、地区/类型/阶段/时间筛选，数据存储于本地 SQLite</>}
        extra={<>
          <Button icon={<DeleteOutlined />} onClick={openRecycle}>回收站</Button>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建项目</Button>
        </>}
      />
      <Card styles={{ body: { paddingBottom: 8 } }}>
        <Space wrap size={12} style={{ marginBottom: 14 }}>
          <Input.Search
            placeholder="搜索项目名称 / 编号 / 招标人"
            allowClear style={{ width: 280 }}
            onSearch={(v) => setQuery((q) => ({ ...q, keyword: v }))}
          />
          <Select style={{ width: 120 }} placeholder="区域" allowClear
            options={options.regions.map((r) => ({ value: r, label: r }))}
            onChange={(v) => setQuery((q) => ({ ...q, region: v ?? '' }))} />
          <Select style={{ width: 120 }} placeholder="工程类型" allowClear
            options={options.project_types.map((r) => ({ value: r, label: r }))}
            onChange={(v) => setQuery((q) => ({ ...q, project_type: v ?? '' }))} />
          <Select style={{ width: 110 }} placeholder="阶段" allowClear
            options={options.stages.map((r) => ({ value: r, label: r }))}
            onChange={(v) => setQuery((q) => ({ ...q, stage: v ?? '' }))} />
          <RangePicker value={dateRange} onChange={(v) => setDateRange(v as [Dayjs, Dayjs] | null)}
            placeholder={['公告起', '公告止']} />
          <Button type={query.favorite ? 'primary' : 'default'} icon={<StarOutlined />}
            onClick={() => setQuery((q) => ({ ...q, favorite: !q.favorite }))}>仅看收藏</Button>
        </Space>
        <Table
          rowKey="id" columns={columns} dataSource={rows} loading={loading}
          locale={{ emptyText: <Empty description="暂无匹配项目" /> }}
          pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条`, showSizeChanger: false }}
          onRow={(r) => ({ onClick: () => undefined, style: { cursor: 'pointer' }, onDoubleClick: () => navigate(`/projects/${r.id}`) })}
        />
      </Card>

      {/* 删除二次确认：展示影响范围，执行软删除 */}
      <Modal
        open={!!delTarget} onCancel={() => setDelTarget(null)}
        onOk={confirmDelete} okText="确认移入回收站" okType="danger"
        cancelText="取消" confirmLoading={delLoading} width={560}
        title={<Space>确认删除项目{delTarget && <b>{delTarget.name}</b>}</Space>}
      >
        {delImpact ? (
          <>
            <Descriptions size="small" column={2} bordered style={{ marginTop: 12 }}>
              <Descriptions.Item label="关联招标文件">{delImpact.documents} 份</Descriptions.Item>
              <Descriptions.Item label="投标要求">{delImpact.requirements} 项</Descriptions.Item>
              <Descriptions.Item label="投标任务">{delImpact.tasks} 项</Descriptions.Item>
              <Descriptions.Item label="时间节点">{delImpact.milestones} 个</Descriptions.Item>
              <Descriptions.Item label="成果文件">{delImpact.deliverables} 份</Descriptions.Item>
            </Descriptions>
            <div style={{ marginTop: 12, fontSize: 12.5, color: '#8a6d3b', background: '#fffbe6', padding: '8px 12px', borderRadius: 6 }}>
              {delImpact.policy}
            </div>
          </>
        ) : (
          <div style={{ padding: 24, textAlign: 'center', color: '#93a1b5' }}>正在获取影响范围…</div>
        )}
      </Modal>

      {/* 回收站：软删除项目恢复 */}
      <Modal
        open={recycleOpen} onCancel={() => setRecycleOpen(false)} footer={null}
        title="回收站（软删除项目）" width={720}
      >
        <Table
          rowKey="id" size="small" dataSource={recycleRows} pagination={false}
          locale={{ emptyText: <Empty description="回收站为空" /> }}
          columns={[
            { title: '项目名称', dataIndex: 'name', ellipsis: true },
            { title: '编号', dataIndex: 'code', width: 130 },
            { title: '删除时间', dataIndex: 'deleted_at', width: 150,
              render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm') },
            {
              title: '操作', key: 'op', width: 130,
              render: (_: unknown, r: TenderProject) => (
                <Space>
                  <Button size="small" type="primary" ghost onClick={() => onRestore(r)}>恢复</Button>
                  <Popconfirm title="彻底物理删除？（文件仍会归档保留，不可再恢复记录）"
                    onConfirm={async () => {
                      try {
                        const res = await deleteProject(r.id, true);
                        message.success(res.message);
                        listDeletedProjects().then(setRecycleRows);
                      } catch (e) { message.error((e as Error).message); }
                    }}>
                    <Button size="small" danger>彻底删除</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Modal>

      <Modal
        title={editing ? '编辑项目' : '新建招标项目'}
        open={modalOpen} onCancel={() => setModalOpen(false)} onOk={submit}
        okText="保存" cancelText="取消" width={640} destroyOnClose
      >
        <Form form={form} layout="vertical" initialValues={emptyForm} style={{ marginTop: 8 }}>
          <Form.Item name="name" label="项目名称" rules={[{ required: true, min: 2, message: '请输入至少 2 个字的项目名称' }]}>
            <Input placeholder="如：深圳XX学校改扩建工程施工总承包" />
          </Form.Item>
          <Space size={12} style={{ display: 'flex' }}>
            <Form.Item name="code" label="项目编号" rules={[{ required: true, message: '请输入项目编号' }]} style={{ width: 190 }}>
              <Input placeholder="如 SZ2026-SG001" />
            </Form.Item>
            <Form.Item name="region" label="区域" rules={[{ required: true }]} style={{ width: 130 }}>
              <Select options={options.regions.map((r) => ({ value: r, label: r }))} showSearch />
            </Form.Item>
            <Form.Item name="project_type" label="工程类型" rules={[{ required: true }]} style={{ width: 130 }}>
              <Select options={['房建', '市政', '交通', '水利', '装饰装修', '机电安装', '园林绿化', '其他'].map((v) => ({ value: v }))} />
            </Form.Item>
          </Space>
          <Space size={12} style={{ display: 'flex' }}>
            <Form.Item name="tender_method" label="招标方式" style={{ width: 130 }}>
              <Select options={['公开招标', '邀请招标'].map((v) => ({ value: v }))} />
            </Form.Item>
            <Form.Item name="stage" label="项目阶段" style={{ width: 130 }}>
              <Select options={['跟踪中', '投标中', '已结束'].map((v) => ({ value: v }))} />
            </Form.Item>
            <Form.Item name="budget" label="预算/控制价（万元）" style={{ width: 190 }}>
              <Input type="number" min={0} placeholder="0" />
            </Form.Item>
          </Space>
          <Form.Item name="range" label="公告发布 ~ 投标截止">
            <RangePicker style={{ width: '100%' }} placeholder={['公告发布日期', '投标截止日期']} />
          </Form.Item>
          <Space size={12} style={{ display: 'flex' }}>
            <Form.Item name="tenderer" label="招标人" style={{ width: 300 }}>
              <Input placeholder="建设单位名称" />
            </Form.Item>
            <Form.Item name="agency" label="代理机构" style={{ width: 300 }}>
              <Input placeholder="招标代理机构" />
            </Form.Item>
          </Space>
          <Form.Item name="description" label="项目概况">
            <Input.TextArea rows={3} placeholder="项目规模、范围等概况信息" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

function r_deadline_warn(v: string | null): boolean {
  if (!v) return false;
  const d = dayjs(v);
  return d.isAfter(dayjs()) && d.diff(dayjs(), 'day') <= 7;
}
