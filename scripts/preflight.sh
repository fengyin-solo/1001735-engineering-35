#!/usr/bin/env bash
# 环境体检：逐项检查本机是否具备复现条件，哪一项没过就说明缺的是什么。
# 默认只查“本地直跑”所需的工具；加 --with-docker 同时检查容器方式。
set -uo pipefail

WITH_DOCKER=0
[ "${1:-}" = "--with-docker" ] && WITH_DOCKER=1
fail=0

check() {
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "[OK]   $name"
  else
    echo "[缺失] $name —— $2"
    fail=1
  fi
}

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== 运行时 =="
if command -v python3 >/dev/null 2>&1; then
  ver="$(python3 -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])')"
  major="$(python3 -c 'import sys;print(sys.version_info[0])')"
  minor="$(command -v python3 >/dev/null && python3 -c 'import sys;print(sys.version_info[1])')"
  if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; }; then
    echo "[OK]   Python ${ver}（基线 3.11.x，容器固定 3.11.16）"
  else
    echo "[缺失] Python ${ver} 低于基线 3.11，请升级（容器镜像 python:3.11.16-slim-bookworm）"
    fail=1
  fi
else
  echo "[缺失] python3 —— 请安装 Python 3.11+（apt: python3 与 python3-venv，或用脚本内 get-pip 引导）"
  fail=1
fi

if command -v node >/dev/null 2>&1; then
  nm="$(node -p 'process.versions.node.split(".")[0]')"
  if [ "$nm" = "20" ]; then
    echo "[OK]   Node $(node --version)（基线 20.20.2，容器固定 node:20.20.2-alpine3.22）"
  else
    echo "[警告] Node 主版本 ${nm}，基线为 20（本机结果可能与容器有差异）"
  fi
else
  echo "[缺失] Node.js —— 请安装 Node 20.x（与容器 node:20.20.2-alpine3.22 对齐）"
  fail=1
fi
check "npm（前端依赖安装）" command -v npm

echo
echo "== 锁文件（依赖版本以它们为准）=="
[ -f "$ROOT/backend/requirements.lock" ] \
  && echo "[OK]   backend/requirements.lock" \
  || { echo "[缺失] backend/requirements.lock —— 后端依赖无法按固定版本复现"; fail=1; }
[ -f "$ROOT/frontend/package-lock.json" ] \
  && echo "[OK]   frontend/package-lock.json" \
  || { echo "[缺失] frontend/package-lock.json —— 前端依赖无法按固定版本复现"; fail=1; }

echo
echo "== 网络（首次装依赖需要）=="
if curl -fsS -m 8 -I -o /dev/null https://pypi.org/simple/; then
  echo "[OK]   可访问 PyPI"
else
  echo "[缺失] 无法访问 https://pypi.org —— 后端依赖装不下来，需配置网络/内网镜像"
  fail=1
fi
if curl -fsS -m 8 -o /dev/null https://registry.npmjs.org/-/ping; then
  echo "[OK]   可访问 npm registry"
else
  echo "[缺失] 无法访问 https://registry.npmjs.org —— 前端依赖装不下来，需配置网络/内网镜像"
  fail=1
fi

if [ "$WITH_DOCKER" -eq 1 ]; then
  echo
  echo "== 容器方式 =="
  check "docker" command -v docker "请安装 Docker Engine"
  if command -v docker >/dev/null 2>&1; then
    if docker compose version >/dev/null 2>&1; then
      echo "[OK]   docker compose 插件（$(docker compose version --short)）"
    else
      echo "[缺失] docker compose 插件 —— 请安装 compose v2（旧的 docker-compose 不适用本仓库）"
      fail=1
    fi
    if docker info >/dev/null 2>&1; then
      echo "[OK]   docker 守护进程在运行"
    else
      echo "[缺失] docker 守护进程不可用 —— 请启动 Docker Desktop / dockerd，并确认当前用户有权限"
      fail=1
    fi
  fi
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "体检通过：可执行 make install（或 scripts/setup-*.sh）准备依赖。"
else
  echo "体检未通过：按上面 [缺失] 项补齐后重试；每一项都注明了缺的是什么。"
fi
exit "$fail"
