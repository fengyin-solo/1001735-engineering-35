#!/usr/bin/env bash
# 前端依赖准备（幂等，可反复执行）：严格按 package-lock.json 安装。
# 锁文件与 package.json 不一致时 npm ci 会直接失败并指出差异，不会悄悄改版本。
set -euo pipefail
cd "$(dirname "$0")/../frontend"

NODE_MAJOR_REQUIRED=20

if ! command -v npm >/dev/null 2>&1; then
  echo "[缺失] 找不到 npm，请先安装 Node.js ${NODE_MAJOR_REQUIRED}.x（与容器镜像 node:20.20.2-alpine 对齐）" >&2
  exit 1
fi

node_major="$(node -p 'process.versions.node.split(".")[0]')"
echo "[OK] Node $(node --version) / npm $(npm --version)"
if [ "$node_major" -ne "$NODE_MAJOR_REQUIRED" ]; then
  echo "[警告] 本机 Node 主版本为 ${node_major}，复现基线为 ${NODE_MAJOR_REQUIRED}.x（容器内固定 20.20.2）；结果可能有差异" >&2
fi

if [ ! -f package-lock.json ]; then
  echo "[缺失] frontend/package-lock.json 不存在，无法按固定版本复现；该文件应由仓库提供" >&2
  exit 1
fi

echo "[步骤] npm ci（严格按 package-lock.json 安装）"
npm ci --no-audit --no-fund
echo "[OK] 前端依赖就绪：node_modules 与锁文件一致"
