/**
 * 本文件的作用是：创建并启动应用的主入口。
 */
import React from "react";
import ReactDOM from "react-dom/client";
import { App as AntApp, ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import "antd/dist/reset.css";
import "./app/styles.css";
import { AppRouter } from "./app/App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: "#d94841",
          borderRadius: 18,
          fontFamily: '"Avenir Next", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
          colorBgLayout: "#f6f4ee",
        },
      }}
    >
      <AntApp>
        <AppRouter />
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>,
);
