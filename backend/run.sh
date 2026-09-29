#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# 依赖一律按锁文件安装：锁文件里的版本就是标准，换机器结果一致。
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -q -r requirements.lock

# 启动方式照旧：本地 uvicorn 监听 127.0.0.1:8000。
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
