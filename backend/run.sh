#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# 依赖准备幂等执行；缺什么会由脚本打印明确说明。版本以 requirements.lock 为准。
if [ ! -x .venv/bin/python ]; then
  ../scripts/setup-backend.sh
fi

# 启动方式照旧：本机回环 127.0.0.1:8000
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
