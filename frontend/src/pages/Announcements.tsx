import { useCallback, useEffect, useState } from 'react';
import {
  Alert, App, Button, Card, Col, DatePicker, Drawer, Empty, Form, Input, Modal, Pagination,
  Radio, Row, Select, Space, Spin, Tag, Timeline,
} from 'antd';
import { CloudDownloadOutlined, ExportOutlined, PlusOutlined } from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import {
  createAnnouncement, fetchFromSource, listAnnouncements, getAnnStats,
} from '../api/modules';
import type { Announcement } from '../api/types';
import { PageHeader, DemoBadge } from '../components/PageHeader';
import { ANN_TYPE_COLOR, fmtAmount, fmtDate } from '../components/statusTags';

const { RangePicker } = DatePicker;
const TYPES = ['全部', '招标公告', '开标公告', '中标公告', '更正公告'];

export default function Announcements() {
  const { message, modal } = App.useApp();
  const [items, setItems] = useState<Announcement[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState('全部');
  const [keyword, setKeyword] = useState('');
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [detail, setDetail] = useState<Announcement | null>(null);
  const [stats, setStats] = useState<{ total: number; by_type: Record<string, number> } | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(() => {
    setLoading(true);
    listAnnouncements({
      keyword, ann_type: tab === '全部' ? '' : tab, page, page_size: 8,
      date_from: dateRange?.[0]?.format('YYYY-MM-DD'), date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
    })
      .then((r) => { setItems(r.items); setTotal(r.total); })
      .finally(() => setLoading(false));
  }, [keyword, tab, page, dateRange]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { getAnnStats().then(setStats).catch(() => undefined); }, []);

  const tryFetch = async () => {
    const r = await fetchFromSource();
    modal.info({
      title: r.ok ? '抓取完成' : '外部数据源未接入',
      content: (
        <div>
          <p>{r.message}</p>
          <p>
            平台参考地址：
            <a href={r.reference_url} target="_blank" rel="noreferrer">
              深圳公共资源交易平台 <ExportOutlined />
            </a>
          </p>
        </div>
      ),
    });
  };

  const submitCreate = async () => {
    const v = await form.validateFields();
    try {
      await createAnnouncement({
        ...v,
        publish_date: v.publish_date ? v.publish_date.format('YYYY-MM-DD') : null,
      });
      message.success('公告已录入');
      setCreateOpen(false);
      form.resetFields();
      load();
      getAnnStats().then(setStats);
    } catch (e) { message.error((e as Error).message); }
  };

  return (
    <div>
      <PageHeader
        title="招标公告中心"
        subtitle={<>共 {total} 条公告记录 · 当前展示为<b style={{ color: '#d46b08' }}>演示数据</b>，真实公告抓取服务待接入</>}
        extra={<>
          <Button icon={<CloudDownloadOutlined />} onClick={tryFetch}>同步外部数据源</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>手动录入公告</Button>
        </>}
      />
      <Alert
        type="warning" showIcon style={{ marginBottom: 16 }}
        message="本页公告均为演示数据，不代表深圳公共资源交易平台真实公示内容"
        description={<>外部数据接入接口已预留（POST /api/announcements/fetch），可在「系统设置 → 数据源配置」中配置后启用；接入前不会以假数据冒充真实公告。可前往 <a href="https://www.szggzy.cn" target="_blank" rel="noreferrer">深圳公共资源交易平台 <ExportOutlined /></a> 查看真实公告。</>}
      />
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {(['招标公告', '开标公告', '中标公告'] as const).map((t) => (
          <Col xs={12} sm={8} lg={6} key={t}>
            <Card size="small">
              <div style={{ color: '#7a8aa3', fontSize: 13 }}>
                <Tag color={ANN_TYPE_COLOR[t]} style={{ marginInlineEnd: 6 }}>{t}</Tag>累计
              </div>
              <div style={{ fontSize: 26, fontWeight: 700, color: '#16233a' }}>
                {stats?.by_type?.[t] ?? '—'}
              </div>
            </Card>
          </Col>
        ))}
        <Col xs={12} sm={8} lg={6}>
          <Card size="small">
            <div style={{ color: '#7a8aa3', fontSize: 13 }}>其中演示数据</div>
            <div style={{ fontSize: 26, fontWeight: 700, color: '#d46b08' }}>{stats?.total ?? '—'} 条</div>
          </Card>
        </Col>
      </Row>

      <Card styles={{ body: { paddingBottom: 12 } }}>
        <Space wrap style={{ marginBottom: 12 }}>
          <Input.Search placeholder="搜索公告标题 / 内容 / 项目编号" allowClear style={{ width: 300 }}
            onSearch={(v) => { setPage(1); setKeyword(v); }} />
          <RangePicker value={dateRange} onChange={(v) => { setPage(1); setDateRange(v as [Dayjs, Dayjs] | null); }}
            placeholder={['发布起', '发布止']} />
        </Space>
        <Radio.Group value={tab} onChange={(e) => { setPage(1); setTab(e.target.value); }}
          style={{ marginBottom: 12 }} options={TYPES.map((t) => ({ value: t, label: t }))} optionType="button" />
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}><Spin /></div>
        ) : items.length ? (
          <Row gutter={[12, 12]}>
            {items.map((a) => (
              <Col xs={24} xl={12} key={a.id}>
                <Card size="small" hoverable onClick={() => setDetail(a)}
                  styles={{ body: { padding: '12px 16px' } }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    <Tag color={ANN_TYPE_COLOR[a.ann_type]} style={{ flex: 'none', marginTop: 2 }}>{a.ann_type}</Tag>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, color: '#22314c', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {a.title}
                      </div>
                      <div style={{ fontSize: 12, color: '#93a1b5', marginTop: 4 }}>
                        {a.project_code || '无编号'} · {fmtDate(a.publish_date)} · {a.source}
                      </div>
                    </div>
                    {a.is_demo && <DemoBadge />}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Empty description="暂无符合条件的公告" />
        )}
        <div style={{ textAlign: 'right', marginTop: 12 }}>
          <Pagination current={page} total={total} pageSize={8} showSizeChanger={false}
            onChange={setPage} showTotal={(t) => `共 ${t} 条`} />
        </div>
      </Card>

      <Drawer
        open={!!detail} onClose={() => setDetail(null)} width={640}
        title={detail ? <Space wrap>{detail.title}{detail.is_demo && <DemoBadge />}</Space> : ''}
      >
        {detail && (
          <>
            <Timeline mode="left" style={{ marginTop: 8 }}
              items={[{
                color: 'blue',
                children: <Space direction="vertical" size={2}>
                  <b>{detail.ann_type} · {detail.source}</b>
                  <span style={{ color: '#7a8aa3' }}>发布日期：{fmtDate(detail.publish_date)}</span>
                </Space>,
              }]} />
            <DescriptionsBlock ann={detail} />
            <div style={{
              background: '#f7f9fc', border: '1px solid #e8edf4', borderRadius: 6,
              padding: 16, whiteSpace: 'pre-wrap', lineHeight: 1.9, fontSize: 13.5,
            }}>
              {detail.content}
            </div>
            {detail.source_url && (
              <div style={{ marginTop: 12 }}>
                <a href={detail.source_url} target="_blank" rel="noreferrer">
                  <Button icon={<ExportOutlined />}>前往来源平台（外部链接）</Button>
                </a>
              </div>
            )}
          </>
        )}
      </Drawer>

      <Modal title="手动录入公告" open={createOpen} onCancel={() => setCreateOpen(false)}
        onOk={submitCreate} okText="保存" cancelText="取消" destroyOnClose>
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}
          initialValues={{ ann_type: '招标公告' }}>
          <Form.Item name="title" label="公告标题" rules={[{ required: true }]}>
            <Input placeholder="公告完整标题" />
          </Form.Item>
          <Space style={{ display: 'flex' }}>
            <Form.Item name="ann_type" label="公告类型" rules={[{ required: true }]}>
              <Select options={TYPES.filter((t) => t !== '全部').map((v) => ({ value: v }))} style={{ width: 130 }} />
            </Form.Item>
            <Form.Item name="project_code" label="关联项目编号">
              <Input placeholder="如 SZ2026-SG001" style={{ width: 180 }} />
            </Form.Item>
            <Form.Item name="publish_date" label="发布日期">
              <DatePicker />
            </Form.Item>
          </Space>
          <Form.Item name="content" label="公告内容">
            <Input.TextArea rows={5} placeholder="粘贴或输入公告正文" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

function DescriptionsBlock({ ann }: { ann: Announcement }) {
  return (
    <div style={{ marginBottom: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13 }}>
      <div style={{ color: '#7a8aa3' }}>项目编号：<b style={{ color: '#22314c' }}>{ann.project_code || '—'}</b></div>
      <div style={{ color: '#7a8aa3' }}>来源：<b style={{ color: '#22314c' }}>{ann.source}</b></div>
      {ann.ann_type === '中标公告' && (
        <>
          <div style={{ color: '#7a8aa3' }}>中标单位：<b style={{ color: '#22314c' }}>{ann.winner || '—'}</b></div>
          <div style={{ color: '#7a8aa3' }}>中标金额：<b style={{ color: '#22314c' }}>{fmtAmount(ann.win_amount)}</b></div>
        </>
      )}
    </div>
  );
}
