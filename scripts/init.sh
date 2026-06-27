#!/bin/bash
# LIS 系统快速启动脚本
set -e

echo "🚀 LIS 实验室信息系统 — 启动中..."
echo ""

# 1. 启动基础设施（SQL Server + EMQX + Redis）
echo "📦 启动基础设施..."
docker compose up -d sqlserver emqx redis

echo "⏳ 等待 SQL Server 启动..."
until docker compose exec sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "Lis@2026Strong!" -C -Q "SELECT 1" > /dev/null 2>&1; do
    echo "  等待中..."
    sleep 5
done
echo "✅ SQL Server 已就绪"

echo "⏳ 等待 EMQX 启动..."
sleep 10
echo "✅ EMQX 已就绪"

# 2. 创建数据库
echo "🗄️  创建数据库..."
docker compose exec sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "Lis@2026Strong!" -C -Q "IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'lis_db') CREATE DATABASE lis_db"
echo "✅ 数据库 lis_db 已创建"

# 3. 安装后端依赖
echo "📦 安装后端依赖..."
cd backend
pip install -r requirements.txt -q
cd ..

# 4. 初始化种子数据
echo "🌱 初始化种子数据..."
cd backend
python -m app.seed
cd ..

echo ""
echo "========================================"
echo "✅ 基础设施已就绪！"
echo ""
echo "  📊 SQL Server:   localhost:1433"
echo "  📡 EMQX:         localhost:1883 (MQTT)"
echo "  🌐 EMQX 管理台:  http://localhost:18083 (admin/public)"
echo "  📦 Redis:        localhost:6379"
echo ""
echo "  👤 默认管理员:   admin / admin123"
echo "  👤 测试技师:     technician / tech123"
echo ""
echo "下一步:"
echo "  1. 启动后端: cd backend && uvicorn app.main:app --reload"
echo "  2. 启动前端: cd frontend && npm install && npm run dev"
echo "  3. 测试 MQTT: cd backend && python -m app.test_mqtt"
echo "========================================"
