/**
 * 本文件的作用是：提供可复用的 SectionSurface 界面组件。
 */
import type { ReactNode } from "react";
import { Typography } from "antd";

interface SectionSurfaceProps {
  title: string;
  description?: string;
  extra?: ReactNode;
  children: ReactNode;
}

export function SectionSurface({ title, description, extra, children }: SectionSurfaceProps) {
  return (
    <section className="section-surface soft-fade">
      <div className="section-header">
        <div>
          <Typography.Title level={4}>{title}</Typography.Title>
          {description ? <Typography.Text type="secondary">{description}</Typography.Text> : null}
        </div>
        {extra}
      </div>
      <div>{children}</div>
    </section>
  );
}
