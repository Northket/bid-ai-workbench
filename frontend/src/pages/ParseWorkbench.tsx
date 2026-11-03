import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert, App, Badge, Button, Card, Descriptions, Empty, Input, InputNumber, Modal, Select,
  Space, Spin, Tag, Tooltip,
} from 'antd';
import {
  ArrowLeftOutlined, CheckOutlined, EditOutlined, ExportOutlined, FileSearchOutlined, SyncOutlined,
} from '@ant-design/icons';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  documentDownloadUrl, exportParseUrl, getLatestParse, getParseTask, resultToRequirement,
  startParse, verifyParseResult,
} from '../api/modules';
import type { ParseLatestResp, ParseResultItem, ParseTaskInfo } from '../api/types';

const CATEGORY_ORDER = ['basic', 'timeline', 'qualification', 'rejection', 'evaluation', 'technical', 'commercial'];
const VERIFY_TAG: Record<string, { label: string; color: string }> = {
  pending: { label: '待核验', color: 'default' },
  confirmed: { label: '已核验', color: 'success' },
  doubtful: { label: '存在疑问', color: 'warning' },
  failed: { label: '提取失败', color: 'error' },
};
const METHOD_LABEL: Record<string, string> = {
  pdf_text: 'PDF文本提取', ocr: 'OCR提取', rule: '规则提取', ai: 'AI语义提取', manual: '人工录入',
};
const CONF_LABEL: Record<string, { label: string; color: string }> = {
  high: { label: '高可信', color: 'green' }, medium: { label: '中可信', color: 'blue' },
  low: { label: '低可信', color: 'orange' },
};

export default function ParseWorkbench() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const docId = Number(id);
  const [data, setData] = useState<ParseLatestResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [pdfPage, setPdfPage] = useState(1);
  const [pageInput, setPageInput] = useState<number | null>(1);
  const [activeCat, setActiveCat] = useState('basic');
  const [parsing, setParsing] = useState(false);
  const [editTarget, setEditTarget] = useState<ParseResultItem | null>(null);
  const [editValue, setEditValue] = useState('');
  const [editStatus, setEditStatus] = useState('confirmed');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(() => {
    getLatestParse(docId).then(setData).catch(() => setData(null)).finally(() => setLoading(false));
  }, [docId]);

  useEffect(() => {
    load();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [load]);

  // 页面打开时任务仍在运行 → 自动轮询
  useEffect(() => {
    if (data?.task?.status === 'running' && !parsing) pollTask(data.task.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.task?.id, data?.task?.status]);

  const pollTask = (taskId: number) => {
    setParsing(true);
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const t: ParseTaskInfo = await getParseTask(taskId);
        if (t.status !== 'running') {
          if (pollRef.current) clearInterval(pollRef.current);
          setParsing(false);
          if (t.status === 'completed') message.success(`解析完成（V${t.version}）`);
          else message.error(`解析失败：${t.error_message || '未知错误'}`);
          load();
        }
      } catch {
        if (pollRef.current) clearInterval(pollRef.current);
        setParsing(false);
      }
    }, 2000);
  };

  const onReparse = async () => {
    try {
      const r = await startParse(docId);
      message.info(r.message);
      pollTask(r.task_id);
    } catch (e) { message.error((e as Error).message); }
  };

  const jumpTo = (page: number | null) => {
    if (page && page > 0) { setPdfPage(page); setPageInput(page); }
  };

  const saveVerify = async () => {
    if (!editTarget) return;
    try {
      await verifyParseResult(editTarget.id, {
        verification_status: editStatus,
        manual_value: editValue,
      });
      message.success('核验已保存（原始提取内容保留不变）');
      setEditTarget(null);
      load();
    } catch (e) { message.error((e as Error).message); }
  };

  const openEdit = (r: ParseResultItem, status: string) => {
    setEditTarget(r);
    setEditValue(r.manual_value || r.value);
    setEditStatus(status);
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 120 }}><Spin size="large" /></div>;

  const task = data?.task ?? null;
  const stats = task?.stats ?? null;
  const categories = data?.categories ?? {};
  const totalItems = Object.values(categories).reduce((s, arr) => s + arr.length, 0);

  const renderResult = (r: ParseResultItem) => (
    <div key={r.id} style={{
      border: '1px solid #e8edf4', borderRadius: 6, padding: '10px 12px', marginBottom: 10,
      borderLeft: `3px solid ${r.verification_status === 'confirmed' ? '#52c41a' : r.verification_status === 'doubtful' ? '#faad14' : '#d4dbe6'}`,
      background: r.is_carried ? '#f6ffed' : '#fff',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
        <Space size={6} wrap>
          <b style={{ color: '#22314c' }}>{r.field_name || r.field_key}</b>
          {r.section_no && <Tag>{r.section_no}</Tag>}
          <Tag color={VERIFY_TAG[r.verification_status]?.color}>
            {VERIFY_TAG[r.verification_status]?.label}
          </Tag>
          {r.is_carried && <Tooltip title={`从 V${r.source_task_id} 任务结转的已核验条目，重新解析不覆盖`}>
            <Tag color="success">已核验·结转</Tag>
          </Tooltip>}
          <Tooltip title={`可信度：${CONF_LABEL[r.confidence]?.label}｜提取方式：${METHOD_LABEL[r.method] || r.method}`}>
            <Tag color={CONF_LABEL[r.confidence]?.color}>{CONF_LABEL[r.confidence]?.label}</Tag>
          </Tooltip>
        </Space>
        <Space size={4}>
          {r.pdf_page && (
            <Button size="small" type="link" onClick={() => jumpTo(r.pdf_page)}>
              跳转 P{r.pdf_page}{r.page_label ? `（印刷${r.page_label}）` : ''}
            </Button>
          )}
          <Tooltip title="标记存在疑问（保留原文）">
            <Button size="small" onClick={() => openEdit(r, 'doubtful')}>疑问</Button>
          </Tooltip>
          <Tooltip title="人工核验确认">
            <Button size="small" type="primary" ghost icon={<CheckOutlined />}
              onClick={() => openEdit(r, 'confirmed')}>核验</Button>
          </Tooltip>
          <Tooltip title="登记为投标要求（待核验）">
            <Button size="small" icon={<EditOutlined />} onClick={async () => {
              try {
                const res = await resultToRequirement(r.id);
                message.success(res.message);
              } catch (e) { message.error((e as Error).message); }
            }} />
          </Tooltip>
        </Space>
      </div>
      <div style={{ fontSize: 13.5, marginTop: 6, whiteSpace: 'pre-wrap', lineHeight: 1.7, color: '#22314c' }}>
        {r.manual_value || r.value || <span style={{ color: '#b3bdcf' }}>（空）</span>}
      </div>
      {r.manual_value && r.original_text && r.manual_value !== r.original_text && (
        <div style={{ fontSize: 12.5, color: '#93a1b5', marginTop: 4 }}>
          原始提取：{r.original_text.slice(0, 120)}
        </div>
      )}
      {r.original_text && (
        <div style={{
          fontSize: 12.5, color: '#5a6b84', background: '#f7f9fc', borderRadius: 4,
          padding: '6px 10px', marginTop: 6, whiteSpace: 'pre-wrap', borderLeft: '3px solid #1668dc',
        }}>
          <span style={{ color: '#93a1b5' }}>原文依据：</span>{r.original_text}
        </div>
      )}
      {r.chapter && (
        <div style={{ fontSize: 12, color: '#93a1b5', marginTop: 4 }}>章节：{r.chapter}</div>
      )}
    </div>
  );

  // 分类导航：换行按钮组（页签过多会横向溢出遮挡左侧阅读区，改用 wrap 按钮组）
  const catButtons = (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
      {CATEGORY_ORDER.map((c) => {
        const n = categories[c]?.length ?? 0;
        return (
          <Button key={c} size="small"
            type={activeCat === c ? 'primary' : 'default'}
            ghost={activeCat === c}
            onClick={() => setActiveCat(c)}>
            {data?.category_names?.[c] ?? c}（{n}）
          </Button>
        );
      })}
    </div>
  );
  const activeItems = categories[activeCat] ?? [];

  return (
    <div style={{ height: 'calc(100vh - 60px - 40px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12, gap: 12, flexWrap: 'wrap' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/documents')}>返回文件中心</Button>
          {task && (
            <span style={{ color: '#5a6b84', fontSize: 13 }}>
              解析任务 V{task.version}
              <Badge style={{ marginLeft: 8 }} status={
                task.status === 'completed' ? 'success' : task.status === 'failed' ? 'error' : 'processing'}
                text={task.status === 'completed' ? '已完成' : task.status === 'failed' ? '失败' : '解析中…'} />
            </span>
          )}
          {parsing && <Spin size="small" />}
        </Space>
        <Space>
          <Button icon={<SyncOutlined />} loading={parsing} onClick={onReparse}
            disabled={!data /* 演示文件无文档对象 */}>重新解析（保留已核验）</Button>
          {task && (
            <a href={exportParseUrl(task.id)} target="_blank" rel="noreferrer">
              <Button icon={<ExportOutlined />}>导出解析结果</Button>
            </a>
          )}
        </Space>
      </div>

      {task?.status === 'failed' && (
        <Alert type="error" showIcon style={{ marginBottom: 12 }}
          message={`解析失败：${task.error_message}`}
          description="可点击「重新解析」重试；请确认文件未损坏、格式受支持（PDF/DOCX/XLSX）。" />
      )}

      <div style={{ flex: 1, display: 'flex', gap: 12, minHeight: 0 }}>
        {/* 左侧：原始文件阅读区 */}
        <div style={{ flex: '0 0 46%', display: 'flex', flexDirection: 'column', minWidth: 380 }}>
          <Card size="small" title={
            <Space>
              <FileSearchOutlined />
              <span>原始文件（浏览器内置阅读器）</span>
            </Space>
          } styles={{ body: { padding: 0, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 } }}
            style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
            extra={
              <Space>
                <InputNumber size="small" min={1} value={pageInput ?? undefined}
                  placeholder="页码" style={{ width: 80 }}
                  onChange={(v) => setPageInput(v)} onPressEnter={() => jumpTo(pageInput)} />
                <Button size="small" onClick={() => jumpTo(pageInput)}>跳转</Button>
              </Space>
            }>
            <iframe
              key={pdfPage}
              src={`${documentDownloadUrl(docId)}#page=${pdfPage}&zoom=90`}
              title="原始文件"
              style={{ width: '100%', flex: 1, border: 'none', minHeight: 0 }}
            />
          </Card>
        </div>

        {/* 右侧：结构化解析结果区 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 420 }}>
          <Card size="small" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}
            styles={{ body: { paddingTop: 4, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 } }}>
            {stats ? (
              <Descriptions size="small" column={4} style={{ marginBottom: 4 }}>
                <Descriptions.Item label="页数">{stats.page_count}</Descriptions.Item>
                <Descriptions.Item label="章节">{stats.chapter_count}</Descriptions.Item>
                <Descriptions.Item label="表格">{stats.table_count}</Descriptions.Item>
                <Descriptions.Item label="结构化条目">{totalItems}</Descriptions.Item>
                <Descriptions.Item label="字符" span={2}>{stats.char_count.toLocaleString()}</Descriptions.Item>
                <Descriptions.Item label="印刷页码识别">{stats.page_label_detected} 页</Descriptions.Item>
                <Descriptions.Item label="扫描页">{stats.image_pages?.length ?? 0}</Descriptions.Item>
              </Descriptions>
            ) : (
              <Alert type="info" showIcon style={{ marginBottom: 8 }}
                message={task ? '任务运行中，完成后自动展示结果' : '该文件尚未解析'} />
            )}
            {!!stats?.warnings?.length && (
              <Alert type="warning" showIcon style={{ marginBottom: 8 }}
                message={stats.warnings[0]}
                description={stats.warnings.length > 1 ? stats.warnings.slice(1).map((w, i) => <div key={i}>· {w}</div>) : undefined} />
            )}
            {task?.file_sha256 && (
              <div style={{ fontSize: 11.5, color: '#93a1b5', marginBottom: 6 }}>
                解析时文件 SHA-256：{task.file_sha256.slice(0, 32)}…
                <Link to="/documents" style={{ marginLeft: 8 }}>（与导入指纹比对可验证原件未被修改）</Link>
              </div>
            )}
            {catButtons}
            <div style={{ flex: 1, minHeight: 0, overflow: 'auto', paddingRight: 4 }}>
              {activeItems.length > 0 ? activeItems.map(renderResult) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="本类别未提取到条目（引擎不猜测，可在原文中人工确认）" />
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* 核验编辑：显示原文，可修改值，原文永不覆盖 */}
      <Modal
        open={!!editTarget} onCancel={() => setEditTarget(null)} onOk={saveVerify}
        okText="保存核验" cancelText="取消" width={640}
        title={<Space>人工核验{editTarget && <b>{editTarget.field_name}</b>}
          {editTarget?.pdf_page && <Tag>原文 P{editTarget.pdf_page}</Tag>}</Space>}
      >
        {editTarget && (
          <>
            <div style={{ fontSize: 12.5, color: '#93a1b5', margin: '8px 0' }}>
              原始提取内容（保留存档，不可修改）：
            </div>
            <div style={{
              background: '#f7f9fc', borderRadius: 6, padding: 10, whiteSpace: 'pre-wrap',
              maxHeight: 140, overflow: 'auto', fontSize: 13, borderLeft: '3px solid #1668dc',
            }}>
              {editTarget.original_text || '（无原文）'}
            </div>
            <div style={{ fontSize: 12.5, color: '#93a1b5', margin: '10px 0 6px' }}>核验后的值（可修改）：</div>
            <Input.TextArea rows={3} value={editValue} onChange={(e) => setEditValue(e.target.value)} />
            <div style={{ margin: '10px 0 0', display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 13 }}>核验状态：</span>
              <Select value={editStatus} style={{ width: 160 }} onChange={setEditStatus}
                options={[
                  { value: 'confirmed', label: '已核验（确认无误）' },
                  { value: 'doubtful', label: '存在疑问（待复核）' },
                  { value: 'failed', label: '提取失败（作废）' },
                  { value: 'pending', label: '重置为待核验' },
                ]} />
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}
