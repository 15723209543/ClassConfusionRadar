# 本文件的作用是：定义当前服务的容器镜像构建步骤。
FROM node:20-alpine

WORKDIR /app

COPY package.json package.json
RUN npm install

COPY . .

EXPOSE 5173
