import type { ThemeConfig } from 'antd';

/** 全局设计令牌：深蓝主色 + 中性深灰，工程数字化平台风格 */
export const BRAND = {
  primary: '#1668dc',
  primaryDeep: '#0e4bab',
  sidebarBg: '#0d1f3c',
  sidebarBgDeep: '#091527',
  sidebarText: '#a7b8d0',
  sidebarActiveBg: 'rgba(22, 104, 220, 0.22)',
  sidebarActiveText: '#ffffff',
  headerHeight: 60,
};

export const themeConfig: ThemeConfig = {
  token: {
    colorPrimary: BRAND.primary,
    colorInfo: BRAND.primary,
    colorBgLayout: '#f4f6fa',
    borderRadius: 6,
    fontSize: 14,
    colorLink: BRAND.primary,
    wireframe: false,
  },
  components: {
    Layout: { siderBg: BRAND.sidebarBg, headerBg: '#ffffff', headerHeight: BRAND.headerHeight },
    Menu: {
      darkItemBg: 'transparent',
      darkSubMenuItemBg: 'transparent',
      darkItemSelectedBg: BRAND.sidebarActiveBg,
      darkItemSelectedColor: BRAND.sidebarActiveText,
      darkItemColor: BRAND.sidebarText,
      darkItemHoverColor: '#e3ecf8',
      itemBorderRadius: 6,
      itemMarginInline: 10,
    },
    Table: { headerBg: '#f7f9fc', headerColor: '#43546e' },
    Card: { paddingLG: 20 },
  },
};
