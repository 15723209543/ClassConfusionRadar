/**
 * 本文件的作用是：组织 SessionCreatePage 页面所需的数据加载与界面结构。
 */
import { useState } from "react";
import { App, Button, Typography } from "antd";
import { Link, useNavigate } from "react-router-dom";
import { createSession } from "../api/sessions";
import { SectionSurface } from "../components/SectionSurface";
import { CreateSessionForm } from "../features/sessions/CreateSessionForm";

export function SessionCreatePage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (payload: {
    title: string;
    course_type: string;
    class_date: string;
    duration_minutes: number;
    notes?: string;
  }) => {
    try {
      setLoading(true);
      const created = await createSession(payload);
      message.success("课堂场次已创建。");
      navigate(`/sessions/${created.id}`);
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-stack">
      <section className="workspace-hero soft-fade">
        <Typography.Title>创建一场可分析的编程课堂</Typography.Title>
        <Typography.Paragraph className="hero-copy">
          建议先围绕一节课配置好标题、课程类型和时长，后续数据上传与分段都会依附到这个课堂场次上。
        </Typography.Paragraph>
        <Button type="link">
          <Link to="/">返回首页</Link>
        </Button>
      </section>

      <SectionSurface
        title="课堂基本信息"
        description="填写本节课的基础信息。"
      >
        <CreateSessionForm loading={loading} onSubmit={handleSubmit} />
      </SectionSurface>
    </div>
  );
}
