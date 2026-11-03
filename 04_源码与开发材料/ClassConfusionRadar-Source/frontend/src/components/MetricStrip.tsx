/**
 * 本文件的作用是：提供可复用的 MetricStrip 界面组件。
 */
import { Progress, Typography } from "antd";

interface MetricItem {
  label: string;
  value: string | number;
  help?: string;
  percent?: number;
}

interface MetricStripProps {
  items: MetricItem[];
}

export function MetricStrip({ items }: MetricStripProps) {
  return (
    <div className="metric-strip">
      {items.map((item) => (
        <div key={item.label} className="metric-tile">
          <Typography.Text type="secondary">{item.label}</Typography.Text>
          <Typography.Title level={3}>{item.value}</Typography.Title>
          {item.help ? <Typography.Text className="metric-help">{item.help}</Typography.Text> : null}
          {typeof item.percent === "number" ? (
            <Progress percent={Math.max(0, Math.min(100, item.percent))} showInfo={false} strokeColor="#d94841" />
          ) : null}
        </div>
      ))}
    </div>
  );
}
