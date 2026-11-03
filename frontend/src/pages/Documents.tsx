import { useCallback, useEffect, useState } from 'react';
import {
  Alert, App, Button, Card, Drawer, Empty, List, Modal, Select, Space, Tag, Tooltip, Upload,
} from 'antd';
import {
  DeleteOutlined, FileExcelOutlined, FilePdfOutlined, FileWordOutlined, InboxOutlined,
  PlayCircleOutlined, UploadOutlined, WarningOutlined,
} from '@ant-design/icons';
import {
  deleteDocument, importPackage, listDocuments, listProjects, parseDocument, updateDocument,
  uploadDocument,
} from '../api/modules';
import { useNavigate } from 'react-router-dom';
import type { DocumentFile, ParseResult, TenderProject } from '../api/types';
import { PageHeader, DemoBadge } from '../components/PageHeader';
import { DOC_STATUS_COLOR, fmtDate, fmtSize } from '../components/statusTags';
import { CATEGORY } from '../components/statusTags';
import dayjs from 'dayjs';

const { Dragger } = Upload;

function TypeIcon({ type }: { type: string }) {
  if (type === 'pdf') return <FilePdfOutlined style={{ color: '#cf1322', fontSize: 18 }} />;
  if (type === 'doc' || type === 'docx') return <FileWordOutlined style={{ color: '#1668dc', fontSize: 18 }} />;
  return <FileExcelOutlined style={{ color: '#0f9d6b', fontSize: 18 }} />;
}

export default function Documents() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [importing, setImporting] = useState(false);
  const [docs, setDocs] = useState<DocumentFile[]>([]);
  const [projects, setProjects] = useState<TenderProject[]>([]);
  const [uploadProject, setUploadProject] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [parsingId, setParsingId] = useState<number | null>(null);
  const [detail, setDetail] = useState<DocumentFile | null>(null);
  const [parseView, setParseView] = useState<ParseResult | null>(null);
  const [linkTarget, setLinkTarget] = useState<{ doc: DocumentFile; project: number | null } | null>(null);

  const load = useCallback(() => {
    listDocuments().then(setDocs).catch(() => message.error('文件列表加载失败'));
  }, [message]);

  useEffect(() => {
    load();
    listProjects().then(setProjects).catch(() => undefined);
  }, [load]);

  const doUpload = async (file: File) => {
    setUploading(true);
    try {
      await uploadDocument(file, uploadProject);
      message.success(`「${file.name}」上传成功`);
      load();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setUploading(false);
    }
    return false;
  };

  const doParse = async (doc: DocumentFile) => {
    setParsingId(doc.id);
    try {
      const r = await parseDocument(doc.id) as { ok: boolean; task_id?: number; message?: string; result?: unknown; error?: string };
      if (r.ok && 'task_id' in r) {
        // 真实文件 → 解析工作台（自动轮询任务状态）
        message.info(r.message || '解析任务已启动');
        navigate(`/documents/${doc.id}/parse`);
      } else if (r.ok && 'result' in r) {
        message.info('演示记录：已生成演示解析结果（详见第一阶段说明）');
        load();
      } else {
        message.error((r as { error?: string }).error || '解析失败');
        load();
      }
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setParsingId(null);
    }
  };

  const doImportPackage = async (file: File) => {
    setImporting(true);
    try {
      const r = await importPackage(file, uploadProject);
      message.success(r.message);
      if (r.meta && Object.values(r.meta).some(Boolean)) {
        message.info(`交易包元数据：${r.meta['项目名称'] || ''}（${r.meta['项目编号'] || '无编号'}）· SHA-256 已记录`);
      }
      load();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setImporting(false);
    }
  };

  const openDetail = async (doc: DocumentFile) => {
    setDetail(doc);
    setParseView(null);
    if (doc.status === '解析完成' && doc.parse_result) {
      try { setParseView(JSON.parse(doc.parse_result)); } catch { /* ignore */ }
    }
  };

  const saveLink = async () => {
    if (!linkTarget) return;
    try {
      await updateDocument(linkTarget.doc.id, { project_id: linkTarget.project });
      message.success('项目关联已更新');
      setLinkTarget(null);
      load();
    } catch (e) { message.error((e as Error).message); }
  };

  return (
    <div>
      <PageHeader
        title="招标文件解析中心"
        subtitle="上传 PDF / Word 招标文件，关联项目并查看解析结果；解析服务接口已预留，当前为演示解析"
      />
      <Alert type="info" showIcon style={{ marginBottom: 16 }}
        message="文档解析服务接入说明"
        description="当前版本支持真实文件上传与本地存储；点击「开始解析」会生成结构化的演示解析结果（明确标注），用于展示解析结果形态。接入真实解析引擎后，同一入口将输出正式解析内容。"
      />
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'stretch' }}>
          <div style={{ flex: 1, minWidth: 320 }}>
            <Dragger
              multiple={false} showUploadList={false} disabled={uploading}
              accept=".pdf,.doc,.docx,.xls,.xlsx"
              beforeUpload={(file) => { void doUpload(file); return false; }}
              customRequest={() => undefined}
            >
              <p className="ant-upload-drag-icon"><UploadOutlined style={{ color: '#1668dc', fontSize: 40 }} /></p>
              <p className="ant-upload-text" style={{ fontWeight: 600 }}>
                {uploading ? '正在上传…' : '点击或拖拽招标文件到此处上传'}
              </p>
              <p className="ant-upload-hint">支持 .pdf / .doc / .docx / .xls / .xlsx，超出大小限制或内容与类型不符将被服务端拒绝</p>
            </Dragger>
          </div>
          <div style={{ width: 280, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 8 }}>
            <div style={{ fontSize: 13, color: '#7a8aa3' }}>上传时关联项目（可选）：</div>
            <Select
              allowClear placeholder="选择关联的招标项目" style={{ width: '100%' }}
              value={uploadProject} onChange={setUploadProject}
              showSearch optionFilterProp="label"
              options={projects.map((p) => ({ value: p.id, label: `${p.name}（${p.code}）` }))}
            />
            <div style={{ fontSize: 12, color: '#93a1b5' }}>
              已上传 {docs.length} 份文件，解析完成 {docs.filter((d) => d.status === '解析完成').length} 份。
            </div>
            <Upload accept=".zip" showUploadList={false} disabled={importing}
              beforeUpload={(f) => { void doImportPackage(f); return false; }}
              customRequest={() => undefined}>
              <Button icon={<InboxOutlined />} loading={importing}
                style={{ marginTop: 4 }}>导入招标文件交易包（.zip）</Button>
            </Upload>
          </div>
        </div>
      </Card>

      <Card title="文件列表" styles={{ body: { paddingTop: 4 } }}>
        <List
          dataSource={docs}
          locale={{ emptyText: <Empty description="暂无文件，请先上传" /> }}
          renderItem={(d) => (
            <List.Item
              actions={[
                <Button key="parse" size="small" type="primary" ghost loading={parsingId === d.id}
                  disabled={d.status === '解析中'}
                  icon={<PlayCircleOutlined />}
                  onClick={() => doParse(d)}>
                  {d.status === '解析完成' ? '重新解析' : '开始解析'}
                </Button>,
                !d.is_demo ? (
                  <Button key="workbench" size="small" type="link" onClick={() => navigate(`/documents/${d.id}/parse`)}>
                    解析工作台
                  </Button>
                ) : null,
                <Button key="detail" size="small" onClick={() => openDetail(d)}>详情</Button>,
                <Button key="link" size="small" onClick={() => setLinkTarget({ doc: d, project: d.project_id })}>关联项目</Button>,
                <Button key="del" size="small" danger icon={<DeleteOutlined />}
                  onClick={() => Modal.confirm({
                    title: '确认删除文件？',
                    content: `「${d.original_name}」的记录与解析结果将一并删除`,
                    okText: '删除', okType: 'danger', cancelText: '取消',
                    onOk: async () => {
                      try { await deleteDocument(d.id); message.success('已删除'); load(); }
                      catch (e) { message.error((e as Error).message); }
                    },
                  })} />,
              ]}
            >
              <List.Item.Meta
                avatar={<TypeIcon type={d.file_type} />}
                title={
                  <Space wrap>
                    <span style={{ fontWeight: 600, color: '#22314c' }}>{d.original_name}</span>
                    <Tag color={DOC_STATUS_COLOR[d.status]}>{d.status}</Tag>
                    {d.is_demo && <Tooltip title="演示记录：无实际上传文件"><DemoBadge /></Tooltip>}
                  </Space>
                }
                description={
                  <span style={{ fontSize: 12.5, color: '#7a8aa3' }}>
                    {d.file_type.toUpperCase()} · {fmtSize(d.size)} · {dayjs(d.uploaded_at).format('YYYY-MM-DD HH:mm')}
                    {' '}· 关联项目：{d.project_name || <span style={{ color: '#b3bdcf' }}>未关联</span>}
                    {d.status === '解析失败' && (
                      <div style={{ color: '#cf1322', marginTop: 4 }}>
                        <WarningOutlined /> {d.error_message}
                      </div>
                    )}
                  </span>
                }
              />
            </List.Item>
          )}
        />
      </Card>

      <Drawer open={!!detail} onClose={() => setDetail(null)} width={640}
        title={detail ? <Space wrap>{detail.original_name}<Tag color={DOC_STATUS_COLOR[detail.status]}>{detail.status}</Tag></Space> : ''}>
        {detail && (
          <>
            <div style={{ fontSize: 13, color: '#5a6b84', marginBottom: 12 }}>
              文件类型 {detail.file_type.toUpperCase()} · 大小 {fmtSize(detail.size)} · 上传于 {fmtDate(detail.uploaded_at)}
              · 关联项目 {detail.project_name || '未关联'}
            </div>
            {detail.status === '解析失败' && (
              <Alert type="error" showIcon style={{ marginBottom: 12 }} message={detail.error_message || '解析失败'} />
            )}
            {parseView ? (
              <>
                <Alert type="warning" showIcon style={{ marginBottom: 12 }} message={parseView.note} />
                {parseView.sections.map((s) => (
                  <Card key={s.title} size="small" title={s.title} style={{ marginBottom: 10 }}>
                    <ul style={{ margin: 0, paddingLeft: 18, lineHeight: 2, fontSize: 13 }}>
                      {s.items.map((i, idx) => <li key={idx}>{i}</li>)}
                    </ul>
                  </Card>
                ))}
                {parseView.suggested_requirements && parseView.suggested_requirements.length > 0 && (
                  <Card size="small" title="建议提取的投标要求（可一键登记）" style={{ marginBottom: 10 }}>
                    {parseView.suggested_requirements.map((s, i) => (
                      <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '4px 0' }}>
                        <Tag color={CATEGORY[s.category].color}>{CATEGORY[s.category].label}</Tag>
                        <span style={{ flex: 1 }}>{s.name}</span>
                        <span style={{ color: '#93a1b5', fontSize: 12 }}>{s.source_text}</span>
                        <Button size="small" type="link" onClick={() => message.info('第一阶段演示：请前往「投标要求管理」手动登记，导入功能下阶段开放')}>
                          登记
                        </Button>
                      </div>
                    ))}
                  </Card>
                )}
              </>
            ) : detail.status === '解析完成' ? (
              <Alert type="warning" showIcon message="解析结果格式异常，请重新解析" />
            ) : (
              <Empty description="尚未解析，请点击「开始解析」生成演示解析结果" />
            )}
          </>
        )}
      </Drawer>

      <Modal
        open={!!linkTarget} title="关联招标项目" okText="保存" cancelText="取消"
        onCancel={() => setLinkTarget(null)} onOk={saveLink}
      >
        <div style={{ margin: '12px 0' }}>
          <div style={{ marginBottom: 8, color: '#5a6b84' }}>
            文件「{linkTarget?.doc.original_name}」关联到：
          </div>
          <Select
            style={{ width: '100%' }} allowClear placeholder="选择项目（清除即为取消关联）"
            showSearch optionFilterProp="label"
            value={linkTarget?.project ?? undefined}
            onChange={(v) => setLinkTarget((t) => t && { ...t, project: v ?? null })}
            options={projects.map((p) => ({ value: p.id, label: `${p.name}（${p.code}）` }))}
          />
        </div>
      </Modal>
    </div>
  );
}
