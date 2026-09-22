# TideNursery-01 · 潮汐育苗台账

海水育苗场「塘口水质采样与投喂事件」台账种子项目（非库存 / 电商 / 医院）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.11 · FastAPI · SQLAlchemy 2 · Pydantic v2 · python-jose · passlib(bcrypt) · uvicorn |
| 前端 | React 18 · Vite · TypeScript · React Router v6 |
| 数据库 | PostgreSQL 15 |
| 部署 | docker-compose · 前端 Nginx 反代 `/api` |

## 端口与账号

| 服务 | 端口 |
| --- | --- |
| 前端 | **3400** |
| 后端 API | **8400** |
| PostgreSQL | **5434** |

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | 场长 |
| `technician` | `123456` | 水质技术员 |

## 一键启动

```bash
cd TideNursery-01
docker compose up --build
```

启动后访问：

- 前端：http://localhost:3400
- 后端健康检查：http://localhost:8400/api/health
- API 文档：http://localhost:8400/docs

后端 entrypoint 流程：等待数据库就绪 → `create_all` 建表 → seed 初始数据 → 启动 uvicorn。

## 功能模块

1. **Auth**：JWT 登录（OAuth2 Password），`/api/auth/login`、`/api/auth/me`
2. **Hatchery 育苗场**：`name`、`seawaterSource`、`notes`
3. **Pond 育苗塘**：`hatcheryId`、`pondCode`、`species`、`volumeM3`、`status(stocked|dry|quarantine)`；同场 `pondCode` 唯一
4. **WaterSample 水质样**：`pondId`、`sampledAt`、`tempC`、`salinityPpt`、`doMgL`、`ph`、`notes`；`doMgL > 0` 且 `ph ∈ [6,9]`，否则返回 **400**。**高盐复测规则**：同一塘口按采样时刻排序的最近两份水样盐度均 **≥ 35 ppt** 时，禁止再登记第三份（返回 **400** 中文拦截原因），须先有复测工单；工单进行中仅允许登记**恰好 1 份**复测水样，且其盐度必须 **< 32 ppt**（≥ 32 返回 400），复测样通过 `workOrderId` 关联工单
5. **FeedEvent 投喂**：`pondId`、`fedAt`、`feedType`、`amountKg`、`operatorName`
6. **WorkOrder 高盐复测工单**：`pondId`、`triggeredAt`、`closedAt`（可空）、`closeNote`（可空）；同一塘口同时至多一张未关闭工单（数据库部分唯一索引 `closed_at IS NULL`）。触发方式两种：① 登记第二份高盐样时系统在同事务**自动建单**；② `POST /api/work-orders` **手动建单**（仅当最近两份均 ≥ 35 且无未关闭工单，否则 400）。`POST /api/work-orders/{id}/close` 关闭工单，`closeNote` 去首尾空白后**至少 4 个字符**；关闭后该塘恢复常规采样
7. **Dashboard**：塘总数、quarantine 数、近 24h 采样数、近 7 日投喂总量 kg、**待复测塘数**（= 有未关闭工单的塘 ∪ 最近两份均 ≥ 35 但尚未建工单的塘）

## 前端页面

Login · Dashboard · Hatcheries · Ponds · WaterSamples · WorkOrders（复测工单） · FeedEvents

> 种子演示：塘口 **A-01** 已预置最近两份高盐样（35.4 / 36.1 ppt）且尚未建工单——在「水质样」页对 A-01 继续采样会被拦截，可一键生成复测工单（或在「复测工单」页手动建单）走完复测关闭流程；B-01 仅有一份低盐样，可连续登记两份 ≥ 35 的水样观察**自动建单**。

> 注意：后端用 `create_all` 建表，不会修改已存在的表结构。升级含本特性的版本时须重建数据卷：`docker compose down -v && docker compose up --build`。

## 本地开发（可选）

```bash
# 数据库（或用 compose 只起 db）
docker compose up -d db

# 后端
cd backend
pip install -r requirements.txt
set DATABASE_URL=postgresql+psycopg2://tidenursery:tidenursery@localhost:5434/tidenursery
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python -c "from app.seed import seed; seed()"
uvicorn app.main:app --reload --port 8400

# 前端
cd frontend
npm install
npm run dev
```

## 目录结构

```
TideNursery-01/
├── docker-compose.yml
├── README.md
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── auth.py
│       ├── seed.py
│       ├── models/（含 work_order.py）
│       ├── schemas/（含 work_order.py）
│       ├── services/（retest.py：35/32 阈值与采样拦截决策树）
│       └── routers/（含 work_orders.py）
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── pages/（含 WorkOrders.tsx 复测工单页）
        ├── components/
        └── api/
```
