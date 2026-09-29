# 特种设备点检运维平台

面向锅炉、压力容器、起重机械、电梯等特种设备的台账建档、日常点检、润滑保养、定期检验与隐患整改的一体化运维后台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

本地环境（依赖版本、容器构建、样例数据初始化、结果核验）的可复现步骤统一见
**[docs/开发环境复现指南.md](docs/开发环境复现指南.md)**：依赖一律以锁文件
（`backend/requirements.lock`、`frontend/package-lock.json`）为准，可用 `make check-env`
先体检缺什么、`make install` 一键准备。

## 目录结构

```text
.
├── backend/                  FastAPI（Python） 后端
│   ├── requirements.txt      直接依赖声明（范围）
│   ├── requirements.lock     依赖锁文件（实际安装版本，以此为准）
│   ├── app/routers/          每个业务模块一组接口
│   ├── app/services/         业务规则与状态流转
│   ├── app/seed.py           样例数据唯一来源（SEED_ROWS）
│   ├── app/seed_cli.py       样例初始化/校验命令（幂等、指纹核验）
│   └── app/store.py          内存数据仓库，启动即装载样例
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── package.json          依赖声明（范围）
│   ├── package-lock.json     依赖锁文件（npm ci 以此为准）
│   ├── src/views/            每个业务模块一个页面
│   ├── src/api/              统一请求封装
│   ├── src/stores/           会话与筛选状态
│   └── vite.config.ts        dev server 配置（open: false）
├── scripts/                  环境体检与依赖准备脚本
├── docs/开发环境复现指南.md    照着做即可复现的完整步骤
├── .gitignore
└── docker-compose.yml
```

## 启动

首次准备环境建议先体检（缺什么会直接说明）并按锁文件装依赖：

```bash
make check-env          # 环境体检；加 ARGS=--with-docker 连容器条件一起查
make install            # 后端装 backend/.venv（requirements.lock），前端 npm ci（package-lock.json）
```

### 后端

```bash
cd backend
./run.sh                # 首次运行会自动创建 .venv 并按 requirements.lock 装依赖
```

健康检查：`curl http://127.0.0.1:8000/api/health`

样例数据为内存装载，重启即恢复基准；初始化与一致性校验：

```bash
make seed-init          # 初始化样例并幂等自检（18 模块共 54 条，反复执行条数不增长）
make verify             # 校验运行中服务条数、压力管道导出条数与列表范围一致
```

### 前端

```bash
cd frontend
npm ci                  # 严格按 package-lock.json 安装（不要用 npm install 覆盖锁版本）
npm run dev
```

前端默认监听 `http://127.0.0.1:5173/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8000`。

### 容器方式

```bash
docker compose up -d --build     # 基础镜像与依赖版本全部固定，详见复现指南
```

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 锅炉设备 | `boiler` | 锅炉设备 | 设备编号、设备名称、额定蒸发量 |
| 压力容器 | `vessel` | 压力容器 | 容器编号、容器名称、设计压力 |
| 压力管道 | `pressurepipe` | 压力管道 | 管道编号、管道名称、管道级别 |
| 起重机械 | `crane` | 起重机械 | 机械编号、机械名称、额定起重量 |
| 电梯设备 | `elevator` | 电梯设备 | 电梯编号、电梯名称、载重规格 |
| 场内机动车辆 | `forklift` | 场内机动车辆 | 车辆编号、车辆名称、动力方式 |
| 点检计划 | `plan` | 点检计划 | 计划编号、点检对象、点检周期 |
| 点检记录 | `spotcheck` | 点检记录 | 点检单号、关联计划、点检设备 |
| 润滑保养 | `lubricate` | 保养记录 | 保养单号、保养设备、润滑点位 |
| 定期检验 | `inspect` | 检验任务 | 检验编号、检验对象、检验类别 |
| 检验报告 | `report` | 检验报告 | 报告编号、关联检验、报告类别 |
| 隐患登记 | `hazard` | 隐患记录 | 隐患编号、涉及设备、隐患类型 |
| 整改闭环 | `rectify` | 整改单 | 整改单号、关联隐患、整改措施 |
| 使用登记 | `register` | 登记记录 | 登记编号、登记设备、使用单位 |
| 作业人员 | `operator` | 作业人员 | 人员编号、人员姓名、所属单位 |
| 备件器材 | `spare` | 备件器材 | 备件编号、备件名称、适用设备 |
| 维保合同 | `contract` | 维保合同 | 合同编号、服务单位、维保设备 |
| 费用结算 | `settle` | 结算单 | 结算单号、关联合同、费用类别 |

## 约定

- 每个模块的前端页面在 `frontend/src/views/<模块>/index.vue`，后端接口在
  `backend/app/routers/<模块>.py`，业务规则在 `backend/app/services/<模块>.py`。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 导出接口与列表共用同一套筛选条件（如压力管道 `/api/pressurepipe/export` 接收相同的
  `keyword`/`status`），返回当前范围的全量条目，`total` 与条目数、列表 `total` 三者一致，
  另存文件条数即列表当前范围。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。
