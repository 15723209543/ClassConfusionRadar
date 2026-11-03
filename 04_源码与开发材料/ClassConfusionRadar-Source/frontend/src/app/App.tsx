/**
 * 本文件的作用是：组织应用顶层结构与公共界面框架。
 */
import { RouterProvider } from "react-router-dom";
import { router } from "../routes";

export function AppRouter() {
  return <RouterProvider router={router} />;
}
