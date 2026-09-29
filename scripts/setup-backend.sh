#!/usr/bin/env bash
# 后端依赖准备（幂等，可反复执行）：
#   1) 缺 .venv 时创建虚拟环境；系统 python 缺 ensurepip 时用 get-pip.py 无 root 引导；
#   2) 依赖版本以 requirements.lock 为准精确安装；
#   3) 哪一步不满足会明确打印缺的是什么并以非零码退出。
set -euo pipefail
cd "$(dirname "$0")/../backend"

PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=11

if ! command -v python3 >/dev/null 2>&1; then
  echo "[缺失] 找不到 python3，请先安装 Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+（与容器镜像 python:3.11.x 对齐）" >&2
  exit 1
fi

py_version="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
py_major="${py_version%%.*}"
py_minor="${py_version##*.}"
if [ "$py_major" -lt "$PYTHON_MIN_MAJOR" ] || { [ "$py_major" -eq "$PYTHON_MIN_MAJOR" ] && [ "$py_minor" -lt "$PYTHON_MIN_MINOR" ]; }; then
  echo "[缺失] 当前 Python ${py_version} 低于要求的 ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}，请升级后重试" >&2
  exit 1
fi
echo "[OK] Python $(python3 --version 2>&1)"

if [ ! -x .venv/bin/python ]; then
  echo "[步骤] 创建虚拟环境 .venv"
  if python3 -m venv .venv 2>/tmp/venv-err.log; then
    :
  else
    reason="$(grep -m1 -v '^[[:space:]]*$' /tmp/venv-err.log || true)"
    echo "[说明] venv 自带 pip 不可用（${reason:-未输出原因}），无需 root：" >&2
    echo "       改用 python3 -m venv --without-pip，再用 get-pip.py 在线引导 pip" >&2
    rm -rf .venv
    python3 -m venv --without-pip .venv
    if ! curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py; then
      echo "[缺失] 下载 get-pip.py 失败：没有公网访问，无法引导 pip；请安装 python3-pip/python3-venv 后重试" >&2
      exit 1
    fi
    .venv/bin/python /tmp/get-pip.py >/dev/null
  fi
fi

if [ ! -f requirements.lock ]; then
  echo "[缺失] backend/requirements.lock 不存在，无法按固定版本复现；该文件应由仓库提供" >&2
  exit 1
fi

echo "[步骤] 按 requirements.lock 安装精确版本"
.venv/bin/python -m pip --version >/dev/null 2>&1 || {
  echo "[缺失] .venv 里没有 pip，请删除 backend/.venv 后重新执行本脚本" >&2
  exit 1
}
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.lock
echo "[OK] 后端依赖就绪：.venv/bin/python -m pip freeze 可查看已锁定版本"
