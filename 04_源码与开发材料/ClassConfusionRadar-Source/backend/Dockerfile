# 本文件的作用是：定义当前服务的容器镜像构建步骤。
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml
RUN pip install --upgrade pip && pip install -e .[dev]

COPY . /app

EXPOSE 8000
