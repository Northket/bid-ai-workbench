import { useEffect, useState } from 'react';
import { Button, Card, Col, Empty, Progress, Row, Space, Spin, Tag } from 'antd';
import { ArrowRightOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import dayjs from 'dayjs';
import { listBidProjects } from '../api/modules';
import type { BidProjectRow } from '../api/types';
import { PageHeader } from '../components/PageHeader';
import { STAGE_COLOR, fmtAmount, fmtDate } from '../components/statusTags';

export default function BidList() {
  const [rows, setRows] = useState<BidProjectRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listBidProjects().then(setRows).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ textAlign: 'center', padding: 120 }}><Spin size="large" /></div>;

  return (
    <div>
      <PageHeader
        title="投标项目管理"
        subtitle={<>共 {rows.length} 个投标项目 · 在项目详情页点击「加入投标管理」可将跟踪项目纳入此处管理</>}
      />
      {rows.length === 0 ? (
        <Card><Empty description="暂无参与投标的项目，可前往招标项目库将项目加入投标管理" /></Card>
      ) : (
        <Row gutter={[16, 16]}>
          {rows.map((b) => {
            const daysLeft = b.deadline ? dayjs(b.deadline).diff(dayjs(), 'day') : null;
            const urgent = daysLeft !== null && daysLeft <= 7;
            return (
              <Col xs={24} md={12} xl={8} key={b.id}>
                <Card hoverable styles={{ body: { padding: 18 } }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                    <Link to={`/bids/${b.id}`} style={{ fontWeight: 600, fontSize: 15, color: '#16233a', flex: 1, minWidth: 0 }}>
                      <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {b.name}
                      </span>
                    </Link>
                    <Tag color={STAGE_COLOR[b.stage]}>{b.stage}</Tag>
                  </div>
                  <div style={{ color: '#7a8aa3', fontSize: 12.5, margin: '6px 0 10px' }}>
                    {b.code} · {b.region} · {b.project_type}
                  </div>
                  <Space size={16} style={{ marginBottom: 10 }}>
                    <span style={{ fontSize: 12.5, color: '#5a6b84' }}>控制价 {fmtAmount(b.budget, 0)}</span>
                    <span style={{ fontSize: 12.5, color: urgent ? '#cf1322' : '#5a6b84', fontWeight: urgent ? 700 : 400 }}>
                      截止 {fmtDate(b.deadline)}
                      {daysLeft !== null && daysLeft >= 0 && `（剩 ${daysLeft} 天）`}
                    </span>
                  </Space>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 12.5, color: '#7a8aa3' }}>
                      任务 {b.task_done}/{b.task_total} · 节点 {b.milestone_count} · 成果 {b.deliverable_count}
                    </span>
                    <Link to={`/bids/${b.id}`}>
                      <Button size="small" type="link">工作区 <ArrowRightOutlined /></Button>
                    </Link>
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <Progress percent={b.progress} size="small"
                      strokeColor={b.progress === 100 ? '#52c41a' : '#1668dc'}
                      format={(p) => `${p}%`} />
                  </div>
                </Card>
              </Col>
            );
          })}
        </Row>
      )}
    </div>
  );
}
