import { useCallback, useEffect, useState } from 'react';
import {
  App, Button, Card, Col, Drawer, Descriptions, Empty, Form, Input, Modal, Pagination, Popconfirm,
  Row, Select, Space, Spin, Statistic, Table, Tag, Upload,
} from 'antd';
import { DownloadOutlined, ReloadOutlined, SearchOutlined, UploadOutlined } from '@ant-design/icons';
import {
  createHistory, deleteHistory, getHistoryStats, historyTemplateUrl, importHistory, listHistory,
} from '../api/modules';
import type { HistoryStats } from '../api/modules';
import type { HistoricalProject } from '../api/types';
import { PageHeader, DemoBadge } from '../components/PageHeader';
import { fmtAmount, fmtDate } from '../components/statusTags';

export default function History() {
  const { message } = App.useApp();
  const [items, setItems] = useState<HistoricalProject[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [projectType, setProjectType] = useState('');
  const [stats, setStats] = useState<HistoryStats | null>(null);
  const [detail, setDetail] = useState<HistoricalProject | null>(null);
  const [importing, setImporting] = useState(false);
  const [addOpen, setAddOpen] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    listHistory({ keyword, project_type: projectType, page, page_size: 10 })
      .then((r) => { setItems(r.items); setTotal(r.total); })
      .finally(() => setLoading(false));
    // 统计口径与列表筛选保持一致（整改 B2）
    getHistoryStats({ keyword, project_type: projectType }).then(setStats).catch(() => undefined);
  }, [keyword, projectType, page]);

  useEffect(() => { load(); }, [load]);

  const doImport = async (file: File) => {
    setImporting(true);
    try {
      const r = await importHistory(file);
      if (r.ok) message.success(r.message);
      else modal_warn(r.message, r.errors);
      setPage(1);
      load();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setImporting(false);
    }
  };

  const modal_warn = (msg: string, errors: string[]) => {
    Modal.warning({
      title: '导入完成（部分失败）',
      content: (
        <div>
          <p>{msg}</p>
          {errors.slice(0, 6).map((e, i) => <p key={i} style={{ color: '#cf1322', fontSize: 12 }}>· {e}</p>)}
        </div>
      ),
    });
  };

  const columns = [
    {
      title: '项目名称', dataIndex: 'project_name', ellipsis: true,
      render: (v: string, r: HistoricalProject) => (
        <a onClick={() => setDetail(r)} style={{ fontWeight: 500 }}>{v}</a>
      ),
    },
    { title: '区域', dataIndex: 'region', width: 95 },
    { title: '类型', dataIndex: 'project_type', width: 90 },
    {
      title: '中标单位', dataIndex: 'winner', width: 200, ellipsis: true,
      render: (v: string) => v || '—',
    },
    {
      title: '中标金额（万元）', dataIndex: 'bid_amount', width: 135, align: 'right' as const,
      render: (v: number) => <b style={{ color: '#1668dc' }}>{v.toLocaleString('zh-CN', { maximumFractionDigits: 1 })}</b>,
    },
    {
      title: '下浮率', key: 'rate', width: 85, align: 'right' as const,
      render: (_: unknown, r: HistoricalProject) =>
        r.control_amount > 0 ? `${((1 - r.bid_amount / r.control_amount) * 100).toFixed(1)}%` : '—',
    },
    { title: '开标日期', dataIndex: 'bid_open_date', width: 105, render: (v: string) => fmtDate(v) },
    {
      title: '', key: 'demo', width: 90,
      render: (_: unknown, r: HistoricalProject) => (r.is_demo ? <DemoBadge /> : <Tag style={{ margin: 0 }}>导入</Tag>),
    },
  ];

  return (
    <div>
      <PageHeader
        title="历史项目数据库"
        subtitle={<>共 {total} 条历史中标记录 · 支持项目/单位/报价多维查询，并为 AI 知识中心提供数据支持（当前含演示数据）</>}
        extra={<>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button icon={<DownloadOutlined />} href={historyTemplateUrl} target="_blank">下载导入模板</Button>
          <Upload accept=".xlsx" showUploadList={false} disabled={importing}
            beforeUpload={(f) => { void doImport(f); return false; }}
            customRequest={() => undefined}>
            <Button icon={<UploadOutlined />} loading={importing}>Excel 导入</Button>
          </Upload>
          <Button type="primary" onClick={() => setAddOpen(true)}>手工新增</Button>
        </>}
      />
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} lg={6}>
          <Card size="small">
            <Statistic title="当前筛选命中" value={stats?.total ?? 0} suffix="条" />
            <div style={{ fontSize: 12, color: '#93a1b5', marginTop: 4 }}>
              {stats ? `统计口径与列表筛选一致${keyword || projectType ? '' : '（当前未筛选）'}` : ''}
            </div>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small">
            <Statistic title="平均中标金额" value={stats?.amount.avg ?? 0} suffix="万元" precision={0}
              valueStyle={{ color: '#1668dc' }} />
            <div style={{ fontSize: 12, color: '#93a1b5', marginTop: 4 }}>
              有效样本 {stats?.amount.valid_count ?? 0} 条（缺失报价不纳入）
            </div>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small">
            <Statistic title="平均下浮率" value={stats?.discount.avg ?? 0} suffix="%" precision={1}
              valueStyle={{ color: '#0f9d6b' }} />
            <div style={{ fontSize: 12, color: '#93a1b5', marginTop: 4 }}>
              有效样本 {stats?.discount.valid_count ?? 0} 条
              {!!stats?.discount.pending_verification_count && (
                <span style={{ color: '#d46b08' }}>；{stats.discount.pending_verification_count} 条口径待核验</span>
              )}
            </div>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small">
            <div style={{ color: '#7a8aa3', fontSize: 13, marginBottom: 4 }}>数据说明</div>
            <div style={{ fontSize: 12.5, color: '#d46b08' }}>
              {stats?.discount.invalid_count
                ? `${stats.discount.invalid_count} 条缺失中标价/控制价，已排除出下浮率统计。`
                : '下浮率 =（控制价−中标价）÷控制价。'}
              含演示数据，可 Excel 导入真实数据替换。
            </div>
          </Card>
        </Col>
      </Row>

      <Card styles={{ body: { paddingBottom: 12 } }}>
        <Space wrap style={{ marginBottom: 14 }}>
          <Input allowClear style={{ width: 300 }} prefix={<SearchOutlined style={{ color: '#93a1b5' }} />}
            placeholder="搜索项目名称 / 中标单位 / 投标单位 / 招标人"
            onPressEnter={(e) => { setPage(1); setKeyword((e.target as HTMLInputElement).value); }}
            onChange={(e) => { if (!e.target.value) { setPage(1); setKeyword(''); } }} />
          <Select style={{ width: 130 }} placeholder="工程类型" allowClear
            options={['房建', '市政', '交通', '水利', '装饰装修', '机电安装', '园林绿化'].map((v) => ({ value: v }))}
            onChange={(v) => { setPage(1); setProjectType(v ?? ''); }} />
        </Space>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}><Spin /></div>
        ) : (
          <Table rowKey="id" columns={columns} dataSource={items} pagination={false}
            locale={{ emptyText: <Empty description="暂无匹配记录" /> }} />
        )}
        <div style={{ textAlign: 'right', marginTop: 12 }}>
          <Pagination current={page} total={total} pageSize={10} showSizeChanger={false}
            onChange={setPage} showTotal={(t) => `共 ${t} 条`} />
        </div>
      </Card>

      <Drawer open={!!detail} onClose={() => setDetail(null)} width={620}
        title={detail ? <Space wrap>{detail.project_name}{detail.is_demo && <DemoBadge />}</Space> : ''}>
        {detail && (
          <>
            <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="项目编号">{detail.project_code || '—'}</Descriptions.Item>
              <Descriptions.Item label="区域 / 类型">{detail.region} · {detail.project_type}</Descriptions.Item>
              <Descriptions.Item label="招标方式">{detail.tender_method}</Descriptions.Item>
              <Descriptions.Item label="招标人">{detail.tenderer || '—'}</Descriptions.Item>
              <Descriptions.Item label="中标单位">
                <b style={{ color: '#1668dc' }}>{detail.winner || '—'}</b>
              </Descriptions.Item>
              <Descriptions.Item label="中标金额">{fmtAmount(detail.bid_amount)}</Descriptions.Item>
              <Descriptions.Item label="招标控制价">{fmtAmount(detail.control_amount)}</Descriptions.Item>
              <Descriptions.Item label="开标日期">{fmtDate(detail.bid_open_date)}</Descriptions.Item>
            </Descriptions>
            <Card size="small" title={`投标单位（${detail.participants.length} 家）`}>
              {detail.participants.length ? (
                <Space wrap>
                  {detail.participants.map((p) => (
                    <Tag key={p} color={p === detail.winner ? 'green' : 'default'}>{p}</Tag>
                  ))}
                </Space>
              ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未记录投标单位" />}
            </Card>
            {detail.remarks && (
              <div style={{ marginTop: 12, fontSize: 12.5, color: '#93a1b5' }}>备注：{detail.remarks}</div>
            )}
            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Popconfirm title="确认删除该条历史记录？" onConfirm={async () => {
                try { await deleteHistory(detail.id); message.success('已删除'); setDetail(null); load(); }
                catch { message.error('删除失败'); }
              }}>
                <Button danger size="small">删除该记录</Button>
              </Popconfirm>
            </div>
          </>
        )}
      </Drawer>

      <AddModal open={addOpen} onClose={() => setAddOpen(false)} onDone={() => { setAddOpen(false); load(); }} />
    </div>
  );
}

function AddModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const submit = async () => {
    const v = await form.validateFields();
    try {
      await createHistory({ ...v, bid_open_date: v.bid_open_date || null });
      message.success('历史项目已新增');
      form.resetFields();
      onDone();
    } catch (e) { message.error((e as Error).message); }
  };
  return (
    <Modal title="手工新增历史项目" open={open} onCancel={onClose} onOk={submit}
      okText="保存" cancelText="取消" destroyOnClose width={560}>
      <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
        <Form.Item name="project_name" label="项目名称" rules={[{ required: true }]}>
          <Input placeholder="历史项目名称" />
        </Form.Item>
        <Space style={{ display: 'flex' }}>
          <Form.Item name="winner" label="中标单位" style={{ width: 260 }}>
            <Input placeholder="中标单位名称" />
          </Form.Item>
          <Form.Item name="bid_amount" label="中标金额（万元）" style={{ width: 150 }}>
            <Input type="number" placeholder="0" />
          </Form.Item>
        </Space>
        <Space style={{ display: 'flex' }}>
          <Form.Item name="region" label="区域" initialValue="深圳市" style={{ width: 130 }}>
            <Input />
          </Form.Item>
          <Form.Item name="project_type" label="工程类型" initialValue="房建" style={{ width: 130 }}>
            <Select options={['房建', '市政', '交通', '水利', '装饰装修', '机电安装', '园林绿化'].map((v) => ({ value: v }))} />
          </Form.Item>
          <Form.Item name="bid_open_date" label="开标日期" style={{ width: 160 }}>
            <Input placeholder="YYYY-MM-DD" />
          </Form.Item>
        </Space>
        <Form.Item name="tenderer" label="招标人">
          <Input placeholder="建设单位" />
        </Form.Item>
      </Form>
    </Modal>
  );
}
