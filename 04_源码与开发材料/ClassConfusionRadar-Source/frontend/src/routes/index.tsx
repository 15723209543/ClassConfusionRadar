/**
 * 本文件的作用是：配置课堂列表、创建课堂和课堂工作台的前端页面路由。
 */
import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "../layouts/AppShell";
import { SessionCreatePage } from "../pages/SessionCreatePage";
import { SessionListPage } from "../pages/SessionListPage";
import { SessionWorkspacePage } from "../pages/SessionWorkspacePage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <SessionListPage /> },
      { path: "sessions/new", element: <SessionCreatePage /> },
      { path: "sessions/:sessionId", element: <SessionWorkspacePage /> },
    ],
  },
]);
