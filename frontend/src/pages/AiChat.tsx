import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert, App, Avatar, Button, Card, Col, Input, Popconfirm, Row, Select, Space, Tag, Tooltip,
} from 'antd';
import {
  DeleteOutlined, FileSearchOutlined, HistoryOutlined, PlusOutlined, RobotOutlined,
  SendOutlined, UserOutlined,
} from '@ant-design/icons';
import {
  deleteChatSession, getAiConfig, getChatSession, listChatSessions, listProjects, sendChat,
} from '../api/modules';
import type { ChatMessage, ChatSession, TenderProject } from '../api/types';
import { MockBadge } from '../components/PageHeader';
import dayjs from 'dayjs';

type CtxType = 'general' | 'project' | 'document' | 'history';

const CTX_META: Record<CtxType, { label: string; icon: React.ReactNode; desc: string }> = {
  general: { label: '通用问答', icon: <RobotOutlined />, desc: '平台使用与流程类问题' },
  project: { label: '项目问答', icon: <UserOutlined />, desc: '选择项目后询问项目要点' },
  document: { label: '招标文件问答', icon: <FileSearchOutlined />, desc: '基于已解析文件的结构化结果回答' },
  history: { label: '历史项目检索', icon: <HistoryOutlined />, desc: '基于历史中标库的统计分析' },
};

interface LocalMsg extends ChatMessage {
  pending?: boolean;
}

export default function AiChat() {
  const { message } = App.useApp();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [current, setCurrent] = useState<number | null>(null);
  const [messages, setMessages] = useState<LocalMsg[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [ctxType, setCtxType] = useState<CtxType>('general');
  const [ctxProject, setCtxProject] = useState<number | null>(null);
  const [projects, setProjects] = useState<TenderProject[]>([]);
  const [config, setConfig] = useState<{ connected: boolean; message: string } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadSessions = useCallback(() => {
    listChatSessions().then(setSessions).catch(() => undefined);
  }, []);
  useEffect(() => { loadSessions(); }, [loadSessions]);
  useEffect(() => {
    listProjects().then(setProjects).catch(() => undefined);
    getAiConfig().then(setConfig).catch(() => undefined);
  }, []);
  useEffect(() => {
    if (current) getChatSession(current).then((s) => setMessages(s.messages ?? [])).catch(() => undefined);
    else setMessages([]);
  }, [current]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text) return;
    if (ctxType === 'project' && !ctxProject) {
      message.warning('项目问答模式请先选择一个项目');
      return;
    }
    setSending(true);
    const optimistic: LocalMsg = {
      id: -Date.now(), session_id: current ?? 0, role: 'user', content: text, is_mock: false,
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, optimistic]);
    setInput('');
    try {
      const r = await sendChat({
        session_id: current,
        context_type: ctxType,
        context_ref: ctxType === 'project' ? String(ctxProject) : '',
        message: text,
      });
      setCurrent(r.session_id);
      const s = await getChatSession(r.session_id);
      setMessages(s.messages ?? []);
      loadSessions();
    } catch (e) {
      message.error((e as Error).message);
      setMessages((m) => m.filter((x) => x.id !== optimistic.id));
    } finally {
      setSending(false);
    }
  };

  const newSession = () => { setCurrent(null); setMessages([]); };

  return (
    <div style={{ height: 'calc(100vh - 60px - 40px)', display: 'flex', flexDirection: 'column' }}>
      <Alert type="warning" showIcon style={{ marginBottom: 12 }}
        message="AI 能力说明：当前为演示阶段，回复由规则引擎基于本地数据库生成，并明确标注「模拟回复」；大模型 API 与向量检索接口已在系统设置中预留配置入口。" />
      <Row gutter={16} style={{ flex: 1, minHeight: 0 }}>
        <Col flex="230px" style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <Card size="small" title="对话会话" styles={{ body: { padding: 8, flex: 1, overflow: 'auto' } }}
            style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
            extra={<Tooltip title="新对话"><Button type="text" size="small" icon={<PlusOutlined />} onClick={newSession} /></Tooltip>}>
            {sessions.length ? (
              sessions.map((s) => (
                <div key={s.id}
                  onClick={() => setCurrent(s.id)}
                  style={{
                    padding: '8px 10px', borderRadius: 6, cursor: 'pointer', marginBottom: 4,
                    background: current === s.id ? '#e8f1fd' : 'transparent',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6,
                  }}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {s.title}
                    </div>
                    <div style={{ fontSize: 11, color: '#93a1b5' }}>
                      {CTX_META[(s.context_type as CtxType) ?? 'general']?.label ?? '通用'} · {dayjs(s.created_at).format('MM-DD')}
                    </div>
                  </div>
                  <Popconfirm title="删除该会话？" onConfirm={async (e) => {
                    e?.stopPropagation();
                    try {
                      await deleteChatSession(s.id);
                      if (current === s.id) newSession();
                      loadSessions();
                    } catch { message.error('删除失败'); }
                  }}>
                    <Button type="text" size="small" danger icon={<DeleteOutlined />}
                      onClick={(e) => e.stopPropagation()} />
                  </Popconfirm>
                </div>
              ))
            ) : (
              <div style={{ color: '#93a1b5', fontSize: 12.5, textAlign: 'center', padding: 20 }}>暂无历史会话</div>
            )}
          </Card>
        </Col>

        <Col flex="auto" style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <Card size="small" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}
            styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, padding: 0 } }}>
            <div style={{ padding: '10px 16px', borderBottom: '1px solid #eef2f8', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              {(Object.keys(CTX_META) as CtxType[]).map((t) => (
                <Button key={t} size="small" type={ctxType === t ? 'primary' : 'default'} ghost={ctxType === t}
                  icon={CTX_META[t].icon} onClick={() => setCtxType(t)}>
                  {CTX_META[t].label}
                </Button>
              ))}
              {ctxType === 'project' && (
                <Select size="small" style={{ minWidth: 240 }} placeholder="选择项目" showSearch optionFilterProp="label"
                  value={ctxProject ?? undefined} onChange={setCtxProject}
                  options={projects.map((p) => ({ value: p.id, label: p.name }))} />
              )}
              <span style={{ marginLeft: 'auto', fontSize: 12, color: '#93a1b5' }}>
                {config && !config.connected && <Tag color="orange">未接入真实大模型</Tag>}
                {CTX_META[ctxType].desc}
              </span>
            </div>

            <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
              {messages.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '60px 0' }}>
                  <Avatar size={56} style={{ background: '#1668dc' }} icon={<RobotOutlined />} />
                  <div style={{ marginTop: 12, fontWeight: 600, fontSize: 15 }}>深圳建设工程投标 AI 知识中心</div>
                  <div style={{ color: '#93a1b5', fontSize: 13, marginTop: 6 }}>
                    选择问答模式后开始提问，例如「学校类房建项目最近中标价什么水平？」
                  </div>
                </div>
              ) : (
                messages.map((m) => (
                  <div key={m.id} style={{ display: 'flex', gap: 10, marginBottom: 16,
                    flexDirection: m.role === 'user' ? 'row-reverse' : 'row' }}>
                    <Avatar style={{ flex: 'none', background: m.role === 'user' ? '#5a6b84' : '#1668dc' }}
                      icon={m.role === 'user' ? <UserOutlined /> : <RobotOutlined />} />
                    <div style={{
                      maxWidth: '78%', padding: '10px 14px', borderRadius: 10, fontSize: 13.5, lineHeight: 1.7,
                      background: m.role === 'user' ? '#1668dc' : '#f5f7fa',
                      color: m.role === 'user' ? '#fff' : '#2b3a55',
                    }}>
                      {m.role === 'assistant' && m.is_mock && (
                        <div style={{ marginBottom: 6 }}><MockBadge /></div>
                      )}
                      <div className="chat-bubble">{m.content}</div>
                    </div>
                  </div>
                ))
              )}
              <div ref={bottomRef} />
            </div>

            <div style={{ borderTop: '1px solid #eef2f8', padding: 12 }}>
              <Space.Compact style={{ width: '100%' }}>
                <Input size="large" value={input} disabled={sending}
                  placeholder={ctxType === 'project' && !ctxProject ? '请先在上方选择项目…' : '输入问题，Enter 发送'}
                  onPressEnter={send} onChange={(e) => setInput(e.target.value)} />
                <Button size="large" type="primary" icon={<SendOutlined />} loading={sending}
                  onClick={send} disabled={!input.trim()}>发送</Button>
              </Space.Compact>
              <div style={{ fontSize: 11.5, color: '#b3bdcf', marginTop: 6 }}>
                模拟回复由本地规则引擎生成，仅用于演示交互形态，不代表真实 AI 分析结论
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
