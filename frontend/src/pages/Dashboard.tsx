import { useEffect, useState } from 'react';
import { Card, Col, Empty, List, Progress, Row, Spin, Tag, Timeline, Typography } from 'antd';
import {
  ApartmentOutlined, BellOutlined, CheckSquareOutlined, FileSearchOutlined, HistoryOutlined,
  RightOutlined, StarFilled,
} from '@ant-design/icons';
import { Link } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import { getDashboard } from '../api/modules';
import type { DashboardData } from '../api/types';
import { PageHeader } from '../components/PageHeader';
import { DOC_STATUS_COLOR, STAGE_COLOR, fmtDate } from '../components/statusTags';
import { BRAND } from '../theme';

const { Text } = Typography;

function StatCard(props: {
  title: string; value: number | string; suffix?: string; icon: React.ReactNode;
  bg: string; color: string; hint: string; to?: string;
}) {
  const body = (
    <Card hoverable styles={{ body: { padding: 18 } }} style={{ height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ color: '#7a8aa3', fontSize: 13 }}>{props.title}</div>
          <div style={{ fontSize: 30, fontWeight: 700, color: '#16233a', marginTop: 6, lineHeight: 1.1 }}>
            {props.value}
            {props.suffix && <span style={{ fontSize: 13, fontWeight: 400, marginLeft: 4, color: '#93a1b5' }}>{props.suffix}</span>}
          </div>
          <div style={{ marginTop: 8, fontSize: 12, color: '#93a1b5' }}>{props.hint}</div>
        </div>
        <div className="stat-icon" style={{ background: props.bg, color: props.color }}>
          {props.icon}
        </div>
      </div>
    </Card>
  );
  return props.to ? <Link to={props.to}>{body}</Link> : body;
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboard()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ textAlign: 'center', padding: 120 }}><Spin size="large" /></div>;
  if (!data) return <Empty description="数据加载失败" />;

  const pieOption = {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, textStyle: { color: '#5a6b84', fontSize: 12 } },
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '44%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      data: data.type_distribution,
      color: ['#1668dc', '#13c2c2', '#722ed1', '#fa8c16', '#52c41a', '#eb2f96', '#f5222d'],
    }],
  };

  const trendOption = {
    tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${v.toLocaleString()} 万元` },
    grid: { left: 8, right: 16, top: 24, bottom: 0, containLabel: true },
    xAxis: { type: 'category', data: data.win_trend.map((t) => t.month), axisLine: { lineStyle: { color: '#cbd5e4' } }, axisLabel: { color: '#7a8aa3' } },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#eef2f8' } },
      axisLabel: {
        color: '#7a8aa3',
        formatter: (v: number) => (v >= 10000 ? `${v / 10000}亿` : `${v}`),
      },
    },
    series: [{
      type: 'bar',
      data: data.win_trend.map((t) => t.amount),
      barWidth: 18,
      itemStyle: { borderRadius: [4, 4, 0, 0], color: BRAND.primary },
    }],
  };

  return (
    <div>
      <PageHeader
        title="早上好，张工"
        subtitle={<>今天是 {dayjs().format('YYYY年MM月DD日 dddd')} · 平台各模块运行正常，以下为项目总览（含演示数据）</>}
      />
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <StatCard title="招标项目" value={data.project_count} suffix="个" icon={<ApartmentOutlined />}
            bg="#e8f1fd" color={BRAND.primary} hint={`收藏 ${data.favorite_count} · 参与投标 ${data.participating_count}`} to="/projects" />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard title="待处理任务" value={data.pending_task_count} suffix="项" icon={<CheckSquareOutlined />}
            bg="#fff4e5" color="#fa8c16" hint={`待完成投标要求 ${data.requirement_pending} 项`} to="/bids" />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard title="解析文件" value={data.document_count} suffix="份" icon={<FileSearchOutlined />}
            bg="#e9f9f2" color="#0f9d6b" hint="解析服务接口已预留" to="/documents" />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard title="历史中标数据" value={data.history_count} suffix="条" icon={<HistoryOutlined />}
            bg="#f3edfd" color="#722ed1" hint={`公告 ${data.announcement_count} 条（演示）`} to="/history" />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={9}>
          <Card title="项目类型分布" style={{ height: '100%' }}>
            {data.type_distribution.length ? (
              <ReactECharts option={pieOption} style={{ height: 262 }} />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={15}>
          <Card title="历史中标金额趋势（按月汇总 · 演示数据）" style={{ height: '100%' }}>
            {data.win_trend.length ? (
              <ReactECharts option={trendOption} style={{ height: 262 }} />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={7}>
          <Card title="最近浏览项目" extra={<Link to="/projects">全部 <RightOutlined /></Link>} styles={{ body: { paddingTop: 8 } }}>
            <List
              dataSource={data.recent_projects}
              renderItem={(p) => (
                <List.Item style={{ padding: '10px 0', borderBottom: '1px dashed #eef2f8' }}>
                  <Link to={`/projects/${p.id}`} style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      {p.favorite && <StarFilled style={{ color: '#faad14', fontSize: 12 }} />}
                      <Text ellipsis style={{ fontWeight: 500, color: '#22314c' }}>{p.name}</Text>
                    </div>
                    <div style={{ fontSize: 12, color: '#93a1b5', marginTop: 2 }}>
                      {p.region} · {p.project_type} · 截止 {fmtDate(p.deadline)}
                    </div>
                  </Link>
                  <Tag color={STAGE_COLOR[p.stage]}>{p.stage}</Tag>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={7}>
          <Card title="最近上传文件" extra={<Link to="/documents">全部 <RightOutlined /></Link>} styles={{ body: { paddingTop: 8 } }}>
            <List
              dataSource={data.recent_documents}
              renderItem={(d) => (
                <List.Item style={{ padding: '10px 0', borderBottom: '1px dashed #eef2f8' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Text ellipsis style={{ fontWeight: 500, color: '#22314c' }}>{d.original_name}</Text>
                    <div style={{ fontSize: 12, color: '#93a1b5', marginTop: 2 }}>
                      {d.project_name || '未关联项目'} · {dayjs(d.uploaded_at).format('MM-DD HH:mm')}
                    </div>
                  </div>
                  <Tag color={DOC_STATUS_COLOR[d.status]}>{d.status}</Tag>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="投标进度概览" extra={<Link to="/bids">投标管理 <RightOutlined /></Link>}>
            {data.bid_progress.length ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {data.bid_progress.slice(0, 5).map((b) => (
                  <div key={b.project_id}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Link to={`/bids/${b.project_id}`} style={{ fontWeight: 500, color: '#22314c', maxWidth: '70%' }}>
                        <Text ellipsis style={{ color: 'inherit' }}>{b.name}</Text>
                      </Link>
                      <span style={{ fontSize: 12, color: '#7a8aa3' }}>
                        {b.done}/{b.total} 项 · {fmtDate(b.deadline)} 截止
                      </span>
                    </div>
                    <Progress
                      percent={b.progress}
                      size="small"
                      strokeColor={b.progress === 100 ? '#52c41a' : BRAND.primary}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无参与投标的项目" />
            )}
            {data.upcoming_milestones.length > 0 && (
              <>
                <div style={{ borderTop: '1px solid #eef2f8', margin: '14px 0 10px' }} />
                <Timeline
                  items={data.upcoming_milestones.slice(0, 3).map((m) => ({
                    color: m.kind === '开标' ? 'red' : 'blue',
                    children: (
                      <div style={{ fontSize: 13 }}>
                        <b>{m.name}</b>
                        <span style={{ color: '#7a8aa3', marginLeft: 8 }}>{fmtDate(m.date)}</span>
                        <div style={{ color: '#93a1b5', fontSize: 12 }}>
                          <BellOutlined /> {m.project_name}
                        </div>
                      </div>
                    ),
                  }))}
                />
              </>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
