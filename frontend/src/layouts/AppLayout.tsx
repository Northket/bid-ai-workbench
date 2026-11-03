import { useMemo, useState } from 'react';
import { Layout, Menu, Tooltip } from 'antd';
import {
  ApartmentOutlined, BellOutlined, DatabaseOutlined, DashboardOutlined, FileSearchOutlined,
  HistoryOutlined, RobotOutlined, SettingOutlined, StarOutlined, TableOutlined,
} from '@ant-design/icons';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { BRAND } from '../theme';

const { Sider, Content, Header } = Layout;

interface NavItem {
  key: string;
  label: string;
  icon: React.ReactNode;
}

const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: '总览',
    items: [{ key: '/', label: '工作台', icon: <DashboardOutlined /> }],
  },
  {
    title: '市场信息',
    items: [
      { key: '/projects', label: '招标项目库', icon: <ApartmentOutlined /> },
      { key: '/announcements', label: '招标公告中心', icon: <BellOutlined /> },
    ],
  },
  {
    title: '投标准备',
    items: [
      { key: '/documents', label: '招标文件解析', icon: <FileSearchOutlined /> },
      { key: '/requirements', label: '投标要求管理', icon: <TableOutlined /> },
    ],
  },
  {
    title: '数据与智能',
    items: [
      { key: '/history', label: '历史项目数据库', icon: <HistoryOutlined /> },
      { key: '/ai', label: 'AI 知识中心', icon: <RobotOutlined /> },
    ],
  },
  {
    title: '项目执行',
    items: [{ key: '/bids', label: '投标项目管理', icon: <StarOutlined /> }],
  },
  {
    title: '系统',
    items: [{ key: '/settings', label: '系统设置', icon: <SettingOutlined /> }],
  },
];

const TITLES: Record<string, string> = {
  '/': '工作台',
  '/projects': '招标项目库',
  '/announcements': '招标公告中心',
  '/documents': '招标文件解析中心',
  '/requirements': '投标要求管理',
  '/history': '历史项目数据库',
  '/ai': 'AI 知识中心',
  '/bids': '投标项目管理',
  '/settings': '系统设置',
};

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const selectedKey = useMemo(() => {
    const path = location.pathname;
    if (path === '/') return '/';
    const match = Object.keys(TITLES)
      .filter((k) => k !== '/' && path.startsWith(k))
      .sort((a, b) => b.length - a.length)[0];
    return match || '/';
  }, [location.pathname]);

  const pageTitle =
    location.pathname.startsWith('/projects/')
      ? '招标项目库 · 项目详情'
      : location.pathname.startsWith('/bids/')
        ? '投标项目管理 · 工作区'
        : TITLES[selectedKey] || '工作台';

  const menuItems = NAV_GROUPS.map((g) => ({
    key: g.title,
    label: <span style={{ fontSize: 12 }}>{g.title}</span>,
    type: 'group' as const,
    children: g.items.map((i) => ({ key: i.key, icon: i.icon, label: i.label })),
  }));

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={224}
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        breakpoint="lg"
        style={{
          background: `linear-gradient(180deg, ${BRAND.sidebarBg} 0%, ${BRAND.sidebarBgDeep} 100%)`,
          position: 'sticky',
          top: 0,
          height: '100vh',
          overflow: 'auto',
        }}
        theme="dark"
      >
        <div className="brand" style={{ padding: collapsed ? 0 : undefined, justifyContent: collapsed ? 'center' : undefined }}>
          <div className="brand-logo">建</div>
          {!collapsed && (
            <div className="brand-text">
              <b>投标 AI 工作台</b>
              <span>深圳建设工程 · 数字化平台</span>
            </div>
          )}
        </div>
        <Menu
          mode="inline"
          theme="dark"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ background: 'transparent', borderInlineEnd: 'none', paddingBottom: 24 }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            borderBottom: '1px solid #e8edf4',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingInline: 24,
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <div style={{ fontSize: 15, fontWeight: 600, color: '#1f2d3d' }}>
            {pageTitle}
            <span style={{ marginLeft: 12, fontSize: 12, fontWeight: 400, color: '#8a97ab' }}>
              深圳建设工程投标 AI 工作台 · 第一阶段演示版
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <DatabaseOutlined style={{ color: BRAND.primary, fontSize: 16 }} />
            <Tooltip title="本地 SQLite 数据库 · 演示数据已就绪">
              <span style={{ color: '#5a6b84', fontSize: 13 }}>数据源：本地库</span>
            </Tooltip>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: '#f2f6fc',
                borderRadius: 999,
                padding: '4px 14px 4px 4px',
              }}
            >
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  background: BRAND.primary,
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 13,
                }}
              >
                张
              </div>
              <span style={{ fontSize: 13, color: '#33445e' }}>张工 · 投标部</span>
            </div>
          </div>
        </Header>
        <Content style={{ padding: 20 }}>
          <div className="page-fade" key={location.pathname}>
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}
