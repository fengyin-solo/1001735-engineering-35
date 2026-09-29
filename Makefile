.PHONY: install check-env backend frontend seed-init seed-check verify up down logs

# 环境体检：哪一步没过会说明缺的是什么（容器项加 ARGS=--with-docker）
check-env:
	./scripts/preflight.sh $(ARGS)

# 一键准备依赖（幂等）：后端/前端都严格按锁文件安装
install:
	./scripts/setup-backend.sh
	./scripts/setup-frontend.sh

# 启动方式照旧：后端 127.0.0.1:8000，前端 127.0.0.1:5173
backend:
	cd backend && ./run.sh

frontend:
	cd frontend && npm run dev

# 样例数据初始化（幂等：反复执行条数不增长）
seed-init:
	cd backend && .venv/bin/python -m app.seed_cli init

# 运行中服务的结果核验：样例条数 + 压力管道导出条数与列表范围一致
seed-check:
	cd backend && .venv/bin/python -m app.seed_cli check --base-url http://127.0.0.1:8000

verify: seed-check

# 容器方式（基础镜像与依赖版本全部固定）
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f
