import { useCallback, useEffect, useState } from 'react';
import {
  App, Badge, Button, Card, Col, Descriptions, Input, Row, Space, Spin, Switch,
  Table, Tabs, Tag, Tooltip,
} from 'antd';
import {
  ClusterOutlined, DatabaseOutlined, ReloadOutlined, SaveOutlined, SettingOutlined,
} from '@ant-design/icons';
import { getSettings, getSystemStatus, updateSetting } from '../api/modules';
import type { SettingRow, SystemStatus } from '../api/types';
import { PageHeader } from '../components/PageHeader';
import dayjs from 'dayjs';

type EditableRow = SettingRow & { editing?: boolean };

const GROUP_META: Record<string, { title: string; desc: string }> = {
  basic: { title: '基础信息', desc: '企业名称、联系方式与默认关注区域' },
  data_source: { title: '数据源配置', desc: '深圳公共资源交易平台等外部数据源接入参数（预留）' },
  model: { title: '模型配置', desc: '大模型 API 与向量检索接口配置入口（预留）' },
  storage: { title: '文件存储', desc: '上传文件本地存储目录与大小限制' },
};

export default function Settings() {
  const { message } = App.useApp();
  const [groups, setGroups] = useState<Record<string, EditableRow[]>>({});
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([getSettings(), getSystemStatus()])
      .then(([g, s]) => {
        const editable: Record<string, EditableRow[]> = {};
        Object.entries(g).forEach(([k, rows]) => {
          editable[k] = rows.map((r) => ({ ...r, editing: false }));
        });
        setGroups(editable);
        setStatus(s);
      })
      .catch(() => message.error('设置加载失败'))
      .finally(() => setLoading(false));
  }, [message]);

  useEffect(() => { load(); }, [load]);

  const save = async (group: string, row: EditableRow, value: string) => {
    setSavingKey(row.key);
    try {
      await updateSetting(row.key, value);
      message.success(`「${row.label}」已保存`);
      setGroups((g) => ({
        ...g,
        [group]: g[group].map((r) => (r.key === row.key ? { ...r, value, editing: false } : r)),
      }));
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setSavingKey(null);
    }
  };

  const renderGroup = (group: string) => {
    const rows = groups[group] ?? [];
    return (
      <Table rowKey="key" dataSource={rows} pagination={false} size="middle"
        locale={{ emptyText: '暂无配置项' }}
        columns={[
          {
            title: '配置项', dataIndex: 'label', width: 280,
            render: (v: string, r: SettingRow) => (
              <Space direction="vertical" size={0}>
                <span style={{ fontWeight: 500 }}>{v}</span>
                <span style={{ fontSize: 12, color: '#93a1b5' }}>{r.key}</span>
              </Space>
            ),
          },
          {
            title: '值', dataIndex: 'value',
            render: (v: string, r: EditableRow) => {
              if (!r.editing) {
                if (r.sensitive) {
                  // 整改 C2：密钥类配置只显示是否已配置，不显示明文
                  return (
                    <Space size={6}>
                      {r.has_value ? <Tag color="success">已配置（隐藏）</Tag> : <Tag>未配置</Tag>}
                      {r.env_override && (
                        <span style={{ fontSize: 12, color: '#93a1b5' }}>
                          支持环境变量 {r.env_override} 优先
                        </span>
                      )}
                    </Space>
                  );
                }
                return <span style={{ color: v ? '#22314c' : '#b3bdcf' }}>{v || '未配置'}</span>;
              }
              const isBool = v === 'true' || v === 'false';
              if (isBool) {
                return (
                  <Switch defaultChecked={v === 'true'} checkedChildren="启用" unCheckedChildren="停用"
                    onChange={(checked) => save(group, r, checked ? 'true' : 'false')} />
                );
              }
              if (r.sensitive) {
                return (
                  <Space.Compact style={{ width: '100%', maxWidth: 420 }}>
                    <Input.Password defaultValue="" placeholder={r.has_value ? '输入新密钥（留空提交=清除）' : '输入密钥'}
                      id={`input-${r.key}`} autoComplete="new-password" />
                    <Button type="primary" icon={<SaveOutlined />} loading={savingKey === r.key}
                      onClick={() => {
                        const el = document.getElementById(`input-${r.key}`) as HTMLInputElement | null;
                        const val = el?.value ?? '';
                        if (!val && r.has_value && !window.confirm('留空提交将清除已配置的密钥，确认继续？')) return;
                        save(group, r, val);
                      }}>保存</Button>
                  </Space.Compact>
                );
              }
              return (
                <Space.Compact style={{ width: '100%', maxWidth: 420 }}>
                  <Input defaultValue={v} placeholder="请输入配置值" id={`input-${r.key}`} />
                  <Button type="primary" icon={<SaveOutlined />} loading={savingKey === r.key}
                    onClick={() => {
                      const el = document.getElementById(`input-${r.key}`) as HTMLInputElement | null;
                      save(group, r, el?.value ?? v);
                    }}>保存</Button>
                </Space.Compact>
              );
            },
          },
          {
            title: '更新时间', dataIndex: 'updated_at', width: 160,
            render: (v: string) => <span style={{ fontSize: 12, color: '#93a1b5' }}>{dayjs(v).format('YYYY-MM-DD HH:mm')}</span>,
          },
          {
            title: '', key: 'op', width: 70,
            render: (_: unknown, r: EditableRow) =>
              r.editing ? (
                <Button size="small" onClick={() => setGroups((g) => ({
                  ...g, [group]: g[group].map((x) => (x.key === r.key ? { ...x, editing: false } : x)),
                }))}>取消</Button>
              ) : (
                <Button size="small" type="link" onClick={() => setGroups((g) => ({
                  ...g, [group]: g[group].map((x) => (x.key === r.key ? { ...x, editing: true } : x)),
                }))}>编辑</Button>
              ),
          },
        ]}
      />
    );
  };

  const tabItems = [
    ...Object.entries(GROUP_META).map(([key, meta]) => ({
      key,
      label: <span><SettingOutlined /> {meta.title}</span>,
      children: (
        <>
          <div style={{ color: '#7a8aa3', fontSize: 13, marginBottom: 12 }}>{meta.desc}</div>
          {renderGroup(key)}
          {(key === 'data_source' || key === 'model') && (
            <div style={{ marginTop: 12, fontSize: 12.5, color: '#d46b08' }}>
              提示：该分组为预留配置入口，保存后暂不会触发真实外部调用；对应服务接入后即可生效。
            </div>
          )}
        </>
      ),
    })),
    {
      key: 'status',
      label: <span><ClusterOutlined /> 运行状态</span>,
      children: status ? (
        <Row gutter={16}>
          <Col xs={24} lg={12}>
            <Card size="small" title="服务状态">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="应用">
                  <Space>{status.app}<Tag color="blue">{status.version}</Tag></Space>
                </Descriptions.Item>
                <Descriptions.Item label="运行环境">
                  {status.platform} · Python {status.python}
                </Descriptions.Item>
                <Descriptions.Item label="FastAPI / SQLAlchemy">
                  {status.fastapi} / {status.sqlalchemy}
                </Descriptions.Item>
                <Descriptions.Item label="后端服务">
                  <Badge status="success" text={`http://127.0.0.1:8000 · ${status.note}`} />
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card size="small" title={
              <Space><DatabaseOutlined /> 数据库与存储</Space>
            } extra={<Button size="small" icon={<ReloadOutlined />} onClick={load}>刷新</Button>}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="SQLite 路径">
                  <span style={{ fontSize: 12, wordBreak: 'break-all' }}>{status.database.path}</span>
                </Descriptions.Item>
                <Descriptions.Item label="数据库大小">{status.database.size_kb} KB</Descriptions.Item>
                <Descriptions.Item label="上传目录">
                  <span style={{ fontSize: 12, wordBreak: 'break-all' }}>{status.storage.upload_dir}</span>
                </Descriptions.Item>
                <Descriptions.Item label="已存储文件">
                  招标文件 {status.storage.tender_docs} 份 · 成果文件 {status.storage.deliverables} 份 · 共 {status.storage.size_mb} MB
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
          <Col span={24} style={{ marginTop: 16 }}>
            <Card size="small" title="数据表记录数">
              <Row gutter={[8, 8]}>
                {Object.entries(status.database.tables).map(([t, c]) => (
                  <Col xs={12} sm={8} md={6} key={t}>
                    <div style={{
                      background: '#f7f9fc', borderRadius: 6, padding: '8px 12px',
                      display: 'flex', justifyContent: 'space-between',
                    }}>
                      <span style={{ fontSize: 12.5, color: '#5a6b84' }}>{t}</span>
                      <b style={{ color: '#1668dc' }}>{c}</b>
                    </div>
                  </Col>
                ))}
              </Row>
            </Card>
          </Col>
        </Row>
      ) : <Spin />,
    },
  ];

  if (loading) return <div style={{ textAlign: 'center', padding: 120 }}><Spin size="large" /></div>;

  return (
    <div>
      <PageHeader
        title="系统设置"
        subtitle="基础信息、数据源、模型接口与文件存储配置；配置保存至本地 SQLite"
        extra={<Tooltip title="重新加载设置与运行状态"><Button icon={<ReloadOutlined />} onClick={load}>刷新</Button></Tooltip>}
      />
      <Card styles={{ body: { paddingTop: 8 } }}>
        <Tabs items={tabItems} defaultActiveKey="basic" />
      </Card>
    </div>
  );
}
