#!/bin/bash
# 一键开发环境启动
set -e

echo "=== 档案智能查询与开放审核系统 — 开发环境启动 ==="
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker Desktop"
    exit 1
fi

# 复制 .env（如果不存在）
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 已创建 .env 文件，请根据需要修改配置"
fi

# 启动
echo "🚀 启动服务..."
docker compose up -d --build

echo ""
echo "⏳ 等待服务就绪..."
sleep 5

# Healthy check
echo ""
echo "=== 服务状态 ==="
docker compose ps

echo ""
echo "=== 访问地址 ==="
echo "📄 API 文档:    http://localhost:8000/docs"
echo "🔍 API 健康检:  http://localhost:8000/api/health"
echo "🖥️  前端页面:    http://localhost:3000"
echo ""
echo "📊 默认管理员:   admin / Admin@123456"
