# LIS 实验室信息系统

## 技术栈

| 组件 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design |
| 后端 | Python FastAPI + SQLAlchemy 2.0 |
| 数据库 | SQL Server 2022 |
| MQTT | EMQX Broker + aiomqtt |
| 缓存 | Redis 7 |
| 部署 | Docker Compose |

## 快速启动

```bash
# 1. 启动基础设施
chmod +x scripts/init.sh
./scripts/init.sh

# 2. 启动后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. 启动前端（新终端）
cd frontend
npm install
npm run dev

# 4. 测试 MQTT
cd backend
python -m app.test_mqtt
```

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| EMQX 管理台 | http://localhost:18083 |

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 检验师 | technician | tech123 |

## 项目结构

```
lis-system/
├── docker-compose.yml      # Docker 编排
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── main.py         # 入口
│   │   ├── config.py       # 配置
│   │   ├── database.py     # 数据库连接
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── schemas/        # Pydantic 模型
│   │   ├── api/v1/         # API 路由
│   │   ├── mqtt/           # MQTT 服务
│   │   └── utils/          # 工具函数
│   └── requirements.txt
├── frontend/               # React 前端
│   ├── src/
│   │   ├── pages/          # 页面组件
│   │   ├── layouts/        # 布局组件
│   │   ├── services/       # API 调用
│   │   └── contexts/       # 状态管理
│   └── package.json
└── scripts/                # 脚本工具
```

## MQTT 协议

### 仪器→LIS 结果上报

Topic: `lis/instrument/{instrument_code}/result`

```json
{
  "msg_id": "uuid-v4",
  "instrument_code": "CHEM-001",
  "timestamp": "2026-06-19T10:30:00+08:00",
  "specimen": {
    "barcode": "SP202606190001"
  },
  "results": [
    {
      "channel": "GLU",
      "item_code": "GLU",
      "value": "5.6",
      "unit": "mmol/L",
      "flag": "N"
    }
  ]
}
```

## 开发计划

- [x] Phase 1: MVP — 核心流程
- [ ] Phase 2: 完善 — 报告模板、危急值告警
- [ ] Phase 3: 质控 — Westgard 规则、L-J 图
- [ ] Phase 4: 高级 — RBAC、ASTM/HL7、HIS 对接
