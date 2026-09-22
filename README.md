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
4. **WaterSample 水质样**：`pondId`、`sampledAt`、`tempC`、`salinityPpt`、`doMgL`、`ph`、`notes`；`doMgL > 0` 且 `ph ∈ [6,9]`，否则返回 **400**
5. **FeedEvent 投喂**：`pondId`、`fedAt`、`feedType`、`amountKg`、`operatorName`
6. **SalinityRetestTicket 高盐复测工单**：盐度连续超标时的复测闭环（规则见下）
7. **Dashboard**：塘总数、quarantine 数、近 24h 采样数、近 7 日投喂总量 kg、**待复测塘数**

### 高盐复测工单触发规则

- **触发阈值 35 ppt**：同一塘口按采样时刻排序，**最近两份水质样盐度均 ≥ 35** 时触发复测工单。
  - 第二份高盐样保存时**自动生成**工单；也可在满足条件时由人工手动生成（`POST /api/salinity-retest-tickets?pondId=`）。
  - 同塘同一时刻**只允许一张未关闭工单**。
- **工单未关闭前限制采样**：
  - 不允许再新建第三份常规水质样（返回 **400**，水质样页展示拦截原因）。
  - 仅允许创建**恰好一份复测水质样**，其**盐度必须 < 32 ppt**；该样标记为「复测样」且不可删除。
  - 已登记复测样后仍须先关闭工单，期间禁止继续采样。
- **关闭工单**：复测样盐度 < 32 ppt 后才可关闭，**关闭说明至少 4 个字**；工单记录所属塘口、触发时刻、关闭时刻（可空）、关闭说明（可空）。
- 塘口列表行显示「待复测」徽标，仪表盘显示「待复测塘数」。
- 种子数据中塘 **A-02** 预置连续两份高盐样（35.5 / 36.2 ppt）及一张未关闭复测工单。

## 前端页面

Login · Dashboard · Hatcheries · Ponds · WaterSamples · RetestTickets · FeedEvents

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
│       ├── models/
│       ├── schemas/
│       └── routers/
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── pages/
        ├── components/
        └── api/
```
