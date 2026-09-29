# 本地开发环境复现指南（压力管道等特种设备点检运维平台）

这份文档把「依赖准备、容器构建、样例数据初始化」固定成照着做就能复现的步骤。
换台干净机器，从第 0 步开始顺序执行即可；每一步都给出**通过判据**和**没过时缺什么**。

- 依赖版本一律以锁文件为准：后端 `backend/requirements.lock`，前端 `frontend/package-lock.json`。
- 样例数据基线是 `backend/app/seed_data.py` 里的 `SEED_ROWS`：初始化幂等，反复执行不会多出条目。
- 本地裸跑与容器里跑出的是同一份结果，可用数据指纹（SHA-256）核对。
- 启动方式不变：后端 `backend/run.sh`（`uvicorn`，`127.0.0.1:8000`），前端 `npm run dev`（`127.0.0.1:5173`，不自动开浏览器）。

> 说明：当前后端是**进程内内存仓库**（`app/store.py`），不落数据库文件，因此不依赖外部
> 数据库或缓存进程；每次启动都从同一份基线装载。下文所有“数据库/缓存版本”都由对应
> 基础镜像与锁文件固定，无需在宿主机预装。

## 0. 前置条件

| 工具 | 要求版本 | 用途 | 缺失时的现象/安装提示 |
| --- | --- | --- | --- |
| Python | 3.11 或 3.12（本地裸跑用 3.11 亦可，容器固定 3.12） | 后端运行时 | `python3: command not found` → 安装 Python 3.11+ |
| Python venv 模块 | 与 Python 同版本 | 建虚拟环境 | 建 venv 报 `ensurepip is not available` → Debian/Ubuntu 执行 `sudo apt install python3.11-venv`（版本号随本机 Python） |
| Node.js | 20.x（与容器 `node:20-alpine` 大版本一致） | 前端运行时 | `node: command not found` → 安装 Node.js 20 LTS |
| npm | 10.x（随 Node 20 自带） | 前端依赖安装 | `npm: command not found` → 重装 Node.js 20 LTS |
| Docker | 24+ 与 Compose v2（仅容器方式需要） | 构建/运行镜像 | `docker: command not found` 或 `docker compose` 报未知命令 → 安装 Docker Engine + Compose 插件；只用本地裸跑可跳过 |

确认：

```bash
python3 --version            # 期望 3.11.x / 3.12.x
node --version               # 期望 v20.x
npm --version                # 期望 10.x
docker compose version       # 仅容器方式需要
```

## 1. 准备依赖（版本以锁文件为准）

### 后端

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
```

- 安装来源是 `requirements.lock`（`==` 精确钉版，共 20 个包含传递依赖），不是 `requirements.txt`。
  `requirements.txt` 只声明允许的版本范围，是升级锁文件时的输入。
- **通过判据**：

  ```bash
  .venv/bin/python -c "import fastapi, uvicorn, pydantic; print(fastapi.__version__, pydantic.__version__)"
  # 期望输出：0.141.1 2.13.5
  ```

- **没过时缺什么**：
  - 建 venv 报 `ensurepip is not available`：缺系统包 `python3.11-venv`（见第 0 步）。
  - `No matching distribution found`：Python 版本过低或网络无法访问 PyPI；锁内包提供
    cp311/cp312 的 manylinux 轮，3.11/3.12 均可安装，不需要编译器。
  - 公司内网：`pip install -i <内网源> -r requirements.lock`，不要改锁文件。

### 前端

```bash
cd frontend
npm ci
```

- `npm ci` 严格按 `package-lock.json` 安装，会先清掉旧的 `node_modules`；
  绝不要用 `npm install` 去“顺手升级”，那会改写锁文件。
- **通过判据**：

  ```bash
  npm run typecheck   # 无输出、退出码 0 即通过
  ```

- **没过时缺什么**：
  - `npm ci` 报 `can only install with an existing package-lock.json`：锁文件没拿到，确认
    `frontend/package-lock.json` 已随仓库检出。
  - 报 `EBADPLATFORM`/网络超时：检查能否访问 `https://registry.npmjs.org/`；内网用
    `npm ci --registry=<内网源>`，锁文件里的 `resolved` 仍指向官方源，需要时由内网镜像代理。

## 2. 初始化并校验样例数据（幂等）

样例数据共 18 个业务模块、每模块 3 条，压力管道固定为
`PRES-0001 / PRES-0002 / PRES-0003`，状态分别是 `待投用 / 在用运行 / 隔离检修`。

在 `backend/` 目录、用第 1 步的虚拟环境执行：

```bash
# 初始化/重置为标准基线。内部会连续装载两次做幂等自检
.venv/bin/python -m app.seed init

# 校验当前数据与基线是否逐条一致（条数 + 内容 + 指纹）
.venv/bin/python -m app.seed verify
```

- **幂等保证**：初始化是「整表替换」而不是追加，无论执行多少次、之前是否手动登记过记录，
  结果都是同样的 18 模块 × 3 条。命令会连做两次装载并比对指纹，不一致直接失败。
- **通过判据**：两条命令都打印
  `样例数据校验通过/已初始化：18 个模块，共 54 条记录`，且两次指纹相同。
  当前标准指纹（基线内容变更才会变）：

  ```text
  5d2b4fc4011face17573f27630fc0b1ef949e5e614393bd61e1ea34fab6fa281
  ```

- **没过时缺什么/差在哪**：`verify` 会逐条列出问题，例如
  `模块 pressurepipe 条数 4 != 标准 3`、`模块 xxx 缺失`，并同时打印当前与标准指纹；
  修复手段就是重跑 `init`。

### 另存快照（条数必须与列表当前范围一致）

```bash
# 导出全部模块，并核对压力管道当前范围是 3 条；条数不符会中止且不落盘
.venv/bin/python -m app.seed snapshot \
  --out seed-snapshot.json --expect pressurepipe=3
```

- 快照内含 `fingerprint`、`counts`、`rows`。`--expect 模块=条数` 可重复给出。
- **通过判据**：打印 `快照已写入 ... 共 54 条记录`；压力管道条数不是 3 时退出码非 0、
  提示 `模块 pressurepipe 导出 N 条，期望 3 条`，不会写出半成品。
- `seed-snapshot.json` 已被 `.gitignore` 忽略，仅供本地/容器间比对。

## 3. 本地启动（方式照旧）

需要两个终端：

```bash
# 终端 1：后端（127.0.0.1:8000）
cd backend && ./run.sh

# 终端 2：前端（127.0.0.1:5173，不自动开浏览器，手工打开）
cd frontend && npm run dev
```

也可用仓库根目录的 Makefile：`make backend`、`make frontend`（`make install` 等价于
第 1 步，`make seed-init / make seed-verify / make snapshot` 等价于第 2 步）。

**通过判据**：

```bash
curl http://127.0.0.1:8000/api/health
# {"ok":true,"app":"特种设备点检运维平台","modules":18}
```

浏览器打开 http://127.0.0.1:5173/ ，进「压力管道管理」应看到 3 条记录；
`/api` 由 Vite 代理到 `http://127.0.0.1:8000`。

**没过时缺什么**：健康检查连接被拒绝 → 后端没起或端口被占，看终端 1 的 traceback；
前端页面接口报错 → 确认后端先启动、地址仍是 `127.0.0.1:8000`。

## 4. 容器构建与运行（与本地同结果）

镜像同样吃锁文件，且基础镜像钉到了 manifest 摘要（`backend/Dockerfile`、
`frontend/Dockerfile` 开头的 `@sha256:...`），不同机器拉到的运行时与依赖完全一致。

后端镜像在构建期会执行 `python -m app.seed verify`：**镜像里的样例数据不过基线校验，
镜像直接构建失败**。

```bash
# 在仓库根目录
docker compose build
docker compose up
```

- 前端容器通过 `VITE_PROXY_TARGET=http://backend:8000` 把 `/api` 代理到后端容器
  （compose 已配 `depends_on: service_healthy`，后端健康检查通过后前端才启动）。
- 启动方式与裸跑一致：后端仍是 `uvicorn app.main:app`，前端仍是 vite dev server。

**通过判据**：

```bash
curl http://127.0.0.1:8000/api/health                       # {"ok":true,...,"modules":18}
curl -s http://127.0.0.1:8000/api/pressurepipe/export \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['total'])"   # 3
```

### 本地与容器是同一份结果

在本地（第 2 步）与容器内各导出一次快照，比对指纹：

```bash
# 容器内
docker compose exec backend python -m app.seed snapshot --out /tmp/in-container.json
docker compose cp backend:/tmp/in-container.json /tmp/in-container.json

# 与本地快照比对（两边都是标准基线时输出 True）
python3 - <<'PY'
import json
a = json.load(open('seed-snapshot.json'))
b = json.load(open('/tmp/in-container.json'))
print(a['fingerprint'] == b['fingerprint'], a['fingerprint'])
PY
```

期望输出 `True 5d2b4fc4...fa281`。指纹不同说明两边代码/基线不一致，
用 `python -m app.seed verify` 定位到具体模块。

## 5. 压力管道列表与另存条数的口径

- 列表接口 `GET /api/pressurepipe` 与导出接口 `GET /api/pressurepipe/export` 走**同一个
  service 筛选逻辑**，导出接受与列表相同的 `keyword`（管道编号）、`status` 参数，只是不分页。
- 因此对任意筛选条件，`导出.total == 导出.items.length == 同条件列表.total`，
  即「另存出来的条数 = 列表当前范围」。页面「导出压力管道清单」按钮会带当前筛选条件请求，
  并在条数对不上时拒绝落盘、提示重新查询。
- 全量 3 条、按 `PRES-0002` 过滤 1 条、按 `隔离检修` 过滤 1 条均已验证一致。
- 压力管道既有业务口径保持不变：状态序列 `待投用 → 在用运行 → 隔离检修 → 已停用`，
  动作 `办理投用 / 安排检修 / 停用管道`；`停用管道` 置 `abnormal=true`；
  登记必填 `管道编号、管道名称、管道级别`，缺字段返回缺了哪几项。

## 6. 升级依赖（改锁文件的唯一正规路径）

1. 后端：改 `backend/requirements.txt` 的范围约束，然后用干净虚拟环境重新解析并冻结：

   ```bash
   cd backend
   python3 -m venv /tmp/relock && /tmp/relock/bin/pip install -r requirements.txt
   /tmp/relock/bin/pip freeze --all > requirements.lock
   ```

2. 前端：改 `frontend/package.json` 后执行 `npm install` 刷新 `package-lock.json`，
   再用 `npm ci` 验证可复现安装，并提交变更后的锁文件。
3. 重新执行第 2、4 步，确认样例指纹与构建期校验仍通过。

## 7. 故障排查速查

| 现象 | 缺的是什么 / 怎么处理 |
| --- | --- |
| `python3 -m venv` 报 ensurepip 不可用 | 缺 `python3.11-venv` 系统包（第 0 步） |
| pip 装包失败、`No matching distribution` | Python 版本不符或无法访问 PyPI；用 3.11/3.12 或配置内网源 |
| `npm ci` 报锁文件缺失/不同步 | 取回/提交 `package-lock.json`；改了 package.json 要重生成锁文件 |
| `seed verify` 提示条数不符 | 内存数据被改过，重跑 `seed init` 整体重置 |
| 快照/导出条数与列表范围不符 | 重新执行查询后再导出；服务端会直接拒绝，不会写出条数错误的文件 |
| `docker compose build` 后端阶段失败 | 构建期 `seed verify` 未过，按日志里的模块差异修 `seed_data.py`，或恢复基线 |
| 容器起不来、前端 502 | 后端健康检查未通过；`docker compose logs backend` 看 traceback |
| 指纹本地与容器不一致 | 两边代码版本不同；确认用的是同一提交，重新 build（基础镜像已钉摘要） |
