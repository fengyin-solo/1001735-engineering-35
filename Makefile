.PHONY: install seed-init seed-verify snapshot backend frontend

# 依赖准备：后端按 requirements.lock、前端按 package-lock.json，版本以锁文件为准。
install:
	cd backend && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.lock
	cd frontend && npm ci

# 样例数据：初始化幂等（整体重置，不会多出条目）；verify 与标准基线逐条核对。
seed-init:
	cd backend && .venv/bin/python -m app.seed init

seed-verify:
	cd backend && .venv/bin/python -m app.seed verify

# 另存快照：条数按 --expect 核对，默认导出全部模块与压力管道当前 3 条范围。
snapshot:
	cd backend && .venv/bin/python -m app.seed snapshot --out seed-snapshot.json --expect pressurepipe=3

# 启动方式照旧。
backend:
	cd backend && ./run.sh

frontend:
	cd frontend && npm run dev
