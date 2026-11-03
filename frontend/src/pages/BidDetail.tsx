import { useCallback, useEffect, useState } from 'react';
import {
  App, Button, Card, Col, DatePicker, Descriptions, Empty, Form, Input, Modal, Popconfirm,
  Progress, Result, Row, Select, Space, Table, Tabs, Tag, Timeline, Upload,
} from 'antd';
import {
  ArrowLeftOutlined, DeleteOutlined, FileDoneOutlined, PlusOutlined, UploadOutlined,
} from '@ant-design/icons';
import { Link, useNavigate, useParams } from 'react-router-dom';
import dayjs from 'dayjs';
import {
  createMilestone, createTask, deleteDeliverable, deleteMilestone, deleteTask, getBidOverview,
  updateTask, uploadDeliverable,
} from '../api/modules';
import type { BidTask, Deliverable, Importance, Milestone, TenderProject } from '../api/types';
import { PageHeader } from '../components/PageHeader';
import { IMPORTANCE, STAGE_COLOR, fmtAmount, fmtDate, fmtSize } from '../components/statusTags';

export default function BidDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const pid = Number(id);
  const [project, setProject] = useState<TenderProject | null>(null);
  const [tasks, setTasks] = useState<BidTask[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [loading, setLoading] = useState(true);
  const [taskModal, setTaskModal] = useState(false);
  const [msModal, setMsModal] = useState(false);
  const [taskForm] = Form.useForm();
  const [msForm] = Form.useForm();

  const load = useCallback(() => {
    getBidOverview(pid)
      .then((r) => {
        setProject(r.project);
        setTasks(r.tasks);
        setMilestones(r.milestones);
        setDeliverables(r.deliverables);
      })
      .catch(() => setProject(null))
      .finally(() => setLoading(false));
  }, [pid]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Card><Table loading pagination={false} /></Card>;
  if (!project)
    return <Result status="404" title="投标项目不存在" extra={<Button onClick={() => navigate('/bids')}>返回列表</Button>} />;

  const done = tasks.filter((t) => t.status === '已完成').length;
  const progress = tasks.length ? Math.round((done / tasks.length) * 100) : 0;

  const submitTask = async () => {
    const v = await taskForm.validateFields();
    try {
      await createTask({
        ...v,
        due_date: v.due_date ? v.due_date.format('YYYY-MM-DD') : null,
      });
      message.success('任务已创建');
      setTaskModal(false);
      taskForm.resetFields();
      load();
    } catch (e) { message.error((e as Error).message); }
  };

  const submitMilestone = async () => {
    const v = await msForm.validateFields();
    try {
      await createMilestone({ ...v, project_id: pid, date: v.date ? v.date.format('YYYY-MM-DD') : null });
      message.success('时间节点已添加');
      setMsModal(false);
      msForm.resetFields();
      load();
    } catch (e) { message.error((e as Error).message); }
  };

  const cycleTask = async (t: BidTask) => {
    const next = t.status === '待办' ? '进行中' : t.status === '进行中' ? '已完成' : '待办';
    try { await updateTask(t.id, { status: next }); load(); } catch { message.error('更新失败'); }
  };

  const doUpload = async (file: File, category: string, version: string) => {
    try {
      await uploadDeliverable(pid, category, version, file);
      message.success(`「${file.name}」已归档`);
      load();
    } catch (e) { message.error((e as Error).message); }
  };

  const taskColumns = [
    {
      title: '任务', dataIndex: 'title', ellipsis: true,
      render: (v: string, r: BidTask) => (
        <Space>
          <span style={{ cursor: 'pointer', fontWeight: 500 }} onClick={() => cycleTask(r)}>{v}</span>
        </Space>
      ),
    },
    { title: '负责人', dataIndex: 'owner', width: 90, render: (v: string) => v || '—' },
    {
      title: '截止', dataIndex: 'due_date', width: 105,
      render: (v: string) => {
        const overdue = v && dayjs(v).isBefore(dayjs(), 'day');
        return <span style={{ color: overdue ? '#cf1322' : undefined }}>{fmtDate(v)}</span>;
      },
    },
    {
      title: '优先级', dataIndex: 'priority', width: 80,
      render: (v: Importance) => {
        const c = IMPORTANCE[v] ?? IMPORTANCE.medium;
        return <Tag color={c.color}>{c.label}</Tag>;
      },
    },
    {
      title: '状态', dataIndex: 'status', width: 110,
      render: (v: string, r: BidTask) => (
        <Select size="small" value={v} style={{ width: 92 }}
          options={['待办', '进行中', '已完成'].map((s) => ({ value: s }))}
          onChange={async (s) => { try { await updateTask(r.id, { status: s }); load(); } catch { message.error('更新失败'); } }} />
      ),
    },
    {
      title: '', key: 'op', width: 60,
      render: (_: unknown, r: BidTask) => (
        <Popconfirm title="删除该任务？" onConfirm={async () => {
          try { await deleteTask(r.id); load(); } catch { message.error('删除失败'); }
        }}>
          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  const delColumns = [
    {
      title: '文件名', dataIndex: 'name', ellipsis: true,
      render: (v: string, r: Deliverable) => (
        <Space><FileDoneOutlined style={{ color: '#1668dc' }} />
          <span style={{ fontWeight: 500 }}>{v}</span>
          {r.file_path ? (
            <a href={`/api/bids/deliverables/${r.id}/download`} target="_blank" rel="noreferrer">下载</a>
          ) : <Tag>演示记录</Tag>}
        </Space>
      ),
    },
    { title: '分类', dataIndex: 'category', width: 110 },
    { title: '版本', dataIndex: 'version', width: 80 },
    { title: '大小', dataIndex: 'size', width: 100, render: (v: number) => fmtSize(v) },
    { title: '归档时间', dataIndex: 'uploaded_at', width: 150, render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm') },
    {
      title: '', key: 'op', width: 60,
      render: (_: unknown, r: Deliverable) => (
        <Popconfirm title="删除该成果文件？" onConfirm={async () => {
          try { await deleteDeliverable(r.id); load(); } catch { message.error('删除失败'); }
        }}>
          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  const tabItems = [
    {
      key: 'tasks',
      label: <span>投标任务清单 <Tag style={{ marginInlineStart: 4 }}>{tasks.length}</Tag></span>,
      children: (
        <>
          <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
            <Space>
              <Progress type="circle" size={52} percent={progress}
                strokeColor={progress === 100 ? '#52c41a' : '#1668dc'} />
              <div style={{ fontSize: 13, color: '#5a6b84' }}>
                已完成 {done} / {tasks.length} 项任务<br />
                <span style={{ color: '#93a1b5', fontSize: 12 }}>点击状态列可直接流转：待办 → 进行中 → 已完成</span>
              </div>
            </Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setTaskModal(true)}>新增任务</Button>
          </div>
          <Table rowKey="id" columns={taskColumns} dataSource={tasks} pagination={false}
            locale={{ emptyText: <Empty description="暂无任务" /> }} />
        </>
      ),
    },
    {
      key: 'milestones',
      label: <span>重要时间节点 <Tag style={{ marginInlineStart: 4 }}>{milestones.length}</Tag></span>,
      children: (
        <>
          <div style={{ textAlign: 'right', marginBottom: 8 }}>
            <Button icon={<PlusOutlined />} onClick={() => setMsModal(true)}>添加节点</Button>
          </div>
          {milestones.length ? (
            <Timeline
              mode="left"
              items={milestones.map((m) => {
                const past = m.date && dayjs(m.date).isBefore(dayjs(), 'day');
                return {
                  color: past ? 'gray' : m.kind === '开标' ? 'red' : 'blue',
                  children: (
                    <div style={{ paddingBottom: 4 }}>
                      <Space>
                        <b>{m.name}</b>
                        <Tag>{m.kind}</Tag>
                        <span style={{ color: '#7a8aa3' }}>{fmtDate(m.date)}</span>
                        <Popconfirm title="删除该节点？" onConfirm={async () => {
                          try { await deleteMilestone(m.id); load(); } catch { message.error('删除失败'); }
                        }}>
                          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                        </Popconfirm>
                      </Space>
                      {m.description && (
                        <div style={{ fontSize: 12.5, color: '#93a1b5', marginTop: 2 }}>{m.description}</div>
                      )}
                    </div>
                  ),
                };
              })}
            />
          ) : (
            <Empty description="暂无时间节点" />
          )}
        </>
      ),
    },
    {
      key: 'files',
      label: <span>成果文件归档 <Tag style={{ marginInlineStart: 4 }}>{deliverables.length}</Tag></span>,
      children: (
        <>
          <div style={{ marginBottom: 12 }}>
            <Space wrap>
              {['投标文件', '技术方案', '商务报价', '资信材料'].map((cat) => (
                <Upload key={cat} showUploadList={false} multiple={false} accept=".pdf,.doc,.docx,.xls,.xlsx"
                  beforeUpload={(f) => { void doUpload(f, cat, 'V1.0'); return false; }}
                  customRequest={() => undefined}>
                  <Button icon={<UploadOutlined />}>上传 · {cat}</Button>
                </Upload>
              ))}
            </Space>
          </div>
          <Table rowKey="id" columns={delColumns} dataSource={deliverables} pagination={false}
            locale={{ emptyText: <Empty description="暂无归档文件" /> }} />
        </>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title={project.name}
        subtitle={<Space wrap>
          <span>{project.code}</span><span>{project.region} · {project.project_type}</span>
          <Tag color={STAGE_COLOR[project.stage]}>{project.stage}</Tag>
          <span style={{ color: '#cf1322', fontWeight: 600 }}>投标截止 {fmtDate(project.deadline)}</span>
        </Space>}
        extra={<>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/bids')}>返回</Button>
          <Link to={`/projects/${project.id}`}><Button>查看招标详情</Button></Link>
        </>}
      />
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={7}>
          <Card title="项目基本信息" size="small">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="招标人">{project.tenderer || '—'}</Descriptions.Item>
              <Descriptions.Item label="代理机构">{project.agency || '—'}</Descriptions.Item>
              <Descriptions.Item label="控制价">{fmtAmount(project.budget)}</Descriptions.Item>
              <Descriptions.Item label="公告日期">{fmtDate(project.publish_date)}</Descriptions.Item>
              <Descriptions.Item label="投标截止">{fmtDate(project.deadline)}</Descriptions.Item>
            </Descriptions>
            {project.description && (
              <div style={{ borderTop: '1px solid #eef2f8', marginTop: 8, paddingTop: 8, fontSize: 12.5, color: '#7a8aa3' }}>
                {project.description}
              </div>
            )}
          </Card>
        </Col>
        <Col xs={24} xl={17}>
          <Card styles={{ body: { paddingTop: 8 } }}>
            <Tabs items={tabItems} defaultActiveKey="tasks" />
          </Card>
        </Col>
      </Row>

      <Modal title="新增投标任务" open={taskModal} onCancel={() => setTaskModal(false)} onOk={submitTask}
        okText="保存" cancelText="取消" destroyOnClose>
        <Form form={taskForm} layout="vertical" style={{ marginTop: 8 }}
          initialValues={{ priority: 'medium', status: '待办' }}>
          <Form.Item name="title" label="任务名称" rules={[{ required: true }]}>
            <Input placeholder="如：编制施工组织设计（技术标）" />
          </Form.Item>
          <Space style={{ display: 'flex' }}>
            <Form.Item name="owner" label="负责人" style={{ width: 140 }}>
              <Input placeholder="如：王工" />
            </Form.Item>
            <Form.Item name="due_date" label="截止日期">
              <DatePicker />
            </Form.Item>
            <Form.Item name="priority" label="优先级" style={{ width: 110 }}>
              <Select options={Object.entries(IMPORTANCE).map(([k, v]) => ({ value: k as Importance, label: v.label }))} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      <Modal title="添加时间节点" open={msModal} onCancel={() => setMsModal(false)} onOk={submitMilestone}
        okText="保存" cancelText="取消" destroyOnClose>
        <Form form={msForm} layout="vertical" style={{ marginTop: 8 }} initialValues={{ kind: '其他' }}>
          <Form.Item name="name" label="节点名称" rules={[{ required: true }]}>
            <Input placeholder="如：投标文件递交截止" />
          </Form.Item>
          <Space style={{ display: 'flex' }}>
            <Form.Item name="date" label="日期"><DatePicker /></Form.Item>
            <Form.Item name="kind" label="类型" style={{ width: 130 }}>
              <Select options={['开标', '截标', '答疑', '澄清', '其他'].map((v) => ({ value: v }))} />
            </Form.Item>
          </Space>
          <Form.Item name="description" label="说明">
            <Input placeholder="补充说明（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
