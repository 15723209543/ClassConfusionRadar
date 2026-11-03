/**
 * 本文件的作用是：定义应用公共页面框架与导航布局。
 */
import { Button, Layout, Space, Typography } from "antd";
import { Link, Outlet, useLocation } from "react-router-dom";

const { Header, Content } = Layout;

export function AppShell() {
  const location = useLocation();
  const inWorkspace = location.pathname.startsWith("/sessions/");

  return (
    <Layout className="app-shell">
      <Header className="topbar">
        <div>
          <Typography.Title level={3} className="brand-title">
            Class Confusion Radar
          </Typography.Title>
          <Typography.Text className="brand-subtitle">
            面向编程课堂的群体困惑识别与再教学辅助
          </Typography.Text>
        </div>
        <Space>
          {inWorkspace ? (
            <Button type="default">
              <Link to="/">返回首页</Link>
            </Button>
          ) : (
            <Button type="primary">
              <Link to="/sessions/new">新建课堂场次</Link>
            </Button>
          )}
        </Space>
      </Header>
      <Content className="content-shell">
        <Outlet />
      </Content>
    </Layout>
  );
}
