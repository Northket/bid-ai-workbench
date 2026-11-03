import { useEffect, useState } from 'react';
import {
  App, Button, Card, Col, Descriptions, Empty, List, Result, Row, Skeleton, Space, Tabs, Tag,
} from 'antd';
import {
  ArrowLeftOutlined, CheckSquareOutlined, FileSearchOutlined, RobotOutlined, StarFilled, StarOutlined,
} from '@ant-design/icons';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  getProject, listAnnouncements, listDocuments, listRequirements, toggleFavorite, updateProject,
} from '../api/modules';
import type { Announcement, DocumentFile, Requirement, TenderProject } from '../api/types';
import { PageHeader } from '../components/PageHeader';
import {
  ANN_TYPE_COLOR, CATEGORY, DOC_STATUS_COLOR, ImportanceTag, REQ_STATUS_COLOR, STAGE_COLOR,
  fmtAmount, fmtDate,
} from '../components/statusTags';

export default function ProjectDetail() {
  const { id } = useParams();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const pid = Number(id);
  const [project, setProject] = useState<TenderProject | null>(null);
  const [anns, setAnns] = useState<Announcement[]>([]);
  const [docs, setDocs] = useState<DocumentFile[]>([]);
  const [reqs, setReqs] = useState<Requirement[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getProject(pid).catch(() => null),
      listAnnouncements({ keyword: '', page_size: 6 }).then(
        (p: { items: Announcement[] }) => p.items.filter((a) => a.project_code).slice(0, 6)),
      listDocuments({ project_id: pid }),
      listRequirements({ project_id: pid }),
    ])
      .then(([p, allAnns, d, r]) => {
        if (!p) { setNotFound(true); return; }
        setProject(p);
        setAnns((allAnns as Announcement[]).filter((a) => a.project_code === p.code));
        setDocs(d);
        setReqs(r);
      })
      .finally(() => setLoading(false));
  }, [pid]);

  if (loading) return <Card><Skeleton active paragraph={{ rows: 8 }} /></Card>;
  if (notFound || !project)
    return <Result status="404" title="项目不存在" extra={<Button onClick={() => navigate('/projects')}>返回项目库</Button>} />;

  const fav = async () => {
    try { setProject(await toggleFavorite(project.id)); } catch { message.error('操作失败'); }
  };
  const toggleParticipating = async () => {
    try {
      const updated = await updateProject(project.id, { participating: !project.participating });
      setProject(updated);
      message.success(updated.participating ? '已加入投标项目管理' : '已移出投标项目管理');
    } catch (e) { message.error((e as Error).message); }
  };

  const reqCards = (['technical', 'business', 'credit'] as const).map((cat) => {
    const list = reqs.filter((r) => r.category === cat);
    return {
      key: cat,
      label: <span>{CATEGORY[cat].label} <Tag style={{ marginInlineStart: 4 }}>{list.length}</Tag></span>,
      children: list.length ? (
        <List
          size="small"
          dataSource={list}
          renderItem={(r) => (
            <List.Item>
              <div style={{ flex: 1, minWidth: 0 }}>
                <Space wrap>
                  <b style={{ color: '#22314c' }}>{r.name}</b>
                  <ImportanceTag value={r.importance} />
                  <Tag color={REQ_STATUS_COLOR[r.status]}>{r.status}</Tag>
                  {r.confirmed && <Tag color="success">已人工确认</Tag>}
                </Space>
                <div style={{ fontSize: 12.5, color: '#5a6b84', marginTop: 4 }}>{r.content}</div>
                <div style={{ fontSize: 12, color: '#93a1b5', marginTop: 2 }}>
                  出处：{r.source_text || '—'} · 页码 {r.page_no || '—'}
                </div>
              </div>
            </List.Item>
          )}
        />
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`暂无${CATEGORY[cat].label}要求`} />
      ),
    };
  });

  return (
    <div>
      <PageHeader
        title={project.name}
        subtitle={<Space wrap>
          <span>{project.code}</span>
          <span>{project.region} · {project.project_type} · {project.tender_method}</span>
          <Tag color={STAGE_COLOR[project.stage]}>{project.stage}</Tag>
          {project.participating && <Tag color="processing">参与投标</Tag>}
        </Space>}
        extra={<>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/projects')}>返回</Button>
          <Button icon={project.favorite ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
            onClick={fav}>{project.favorite ? '已收藏' : '收藏'}</Button>
          <Button icon={<CheckSquareOutlined />} onClick={toggleParticipating}>
            {project.participating ? '移出投标管理' : '加入投标管理'}
          </Button>
          {project.participating && (
            <Button type="primary" onClick={() => navigate(`/bids/${project.id}`)}>进入投标工作区</Button>
          )}
        </>}
      />
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="项目信息" size="small">
            <Descriptions column={{ xs: 1, sm: 2 }} size="small">
              <Descriptions.Item label="招标人">{project.tenderer || '—'}</Descriptions.Item>
              <Descriptions.Item label="代理机构">{project.agency || '—'}</Descriptions.Item>
              <Descriptions.Item label="预算/控制价">{fmtAmount(project.budget)}</Descriptions.Item>
              <Descriptions.Item label="招标方式">{project.tender_method}</Descriptions.Item>
              <Descriptions.Item label="公告日期">{fmtDate(project.publish_date)}</Descriptions.Item>
              <Descriptions.Item label="投标截止">
                <span style={{ color: '#cf1322', fontWeight: 600 }}>{fmtDate(project.deadline)}</span>
              </Descriptions.Item>
              <Descriptions.Item label="项目概况" span={2}>{project.description || '—'}</Descriptions.Item>
            </Descriptions>
          </Card>
          <Card title="关联招标文件" size="small" style={{ marginTop: 16 }}
            extra={<Link to="/documents">前往解析中心</Link>}>
            {docs.length ? (
              <List size="small" dataSource={docs} renderItem={(d) => (
                <List.Item>
                  <Space><FileSearchOutlined style={{ color: '#1668dc' }} />{d.original_name}</Space>
                  <Tag color={DOC_STATUS_COLOR[d.status]}>{d.status}</Tag>
                </List.Item>
              )} />
            ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚未上传招标文件" />}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="关联公告（演示数据）" size="small">
            {anns.length ? (
              <List size="small" dataSource={anns} renderItem={(a) => (
                <List.Item>
                  <Link to="/announcements" style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {a.title}
                    </span>
                  </Link>
                  <Tag color={ANN_TYPE_COLOR[a.ann_type]}>{a.ann_type}</Tag>
                </List.Item>
              )} />
            ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无关联公告" />}
          </Card>
          <Card size="small" style={{ marginTop: 16 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <Button block icon={<RobotOutlined />} onClick={() => navigate('/ai')}>
                就此项目咨询 AI（项目问答）
              </Button>
              <div style={{ fontSize: 12, color: '#93a1b5' }}>
                AI 知识中心当前为演示阶段，回复由规则引擎生成并标注「模拟回复」。
              </div>
            </div>
          </Card>
        </Col>
        <Col span={24}>
          <Card title="投标要求（技术 / 商务 / 资信）" size="small"
            extra={<Link to="/requirements">前往要求管理</Link>}>
            <Tabs items={reqCards} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
