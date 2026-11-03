import type { ReactNode } from 'react';
import { Tag } from 'antd';

export function PageHeader({
  title,
  subtitle,
  extra,
}: {
  title: string;
  subtitle?: ReactNode;
  extra?: ReactNode;
}) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 16,
        gap: 16,
        flexWrap: 'wrap',
      }}
    >
      <div>
        <div style={{ fontSize: 20, fontWeight: 600, color: '#16233a' }}>{title}</div>
        {subtitle && (
          <div style={{ marginTop: 6, fontSize: 13, color: '#7a8aa3' }}>{subtitle}</div>
        )}
      </div>
      {extra && <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>{extra}</div>}
    </div>
  );
}

export function DemoBadge({ text = '演示数据' }: { text?: string }) {
  return (
    <Tag color="orange" style={{ marginInlineEnd: 0 }}>
      {text}
    </Tag>
  );
}

export function MockBadge() {
  return (
    <Tag color="purple" style={{ marginInlineEnd: 0 }}>
      模拟回复
    </Tag>
  );
}
