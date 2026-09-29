# 后端镜像：依赖以 requirements.lock 为准，基础镜像钉到 manifest 摘要，
# 保证任何机器上 docker build 出来的运行时与依赖版本一致。
# 摘要对应 docker.io/library/python:3.12-slim（多架构 manifest list）。
FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

# 先装依赖：只要锁文件不变，这一层就走缓存。
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY . .

# 构建期校验：镜像里的样例数据必须与标准基线逐条一致（含压力管道 3 条），
# 数据被改坏时镜像直接构建失败，并打印标准指纹便于和本地比对。
RUN python -m app.seed verify

# 非 root 运行。
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /srv/app
USER appuser

EXPOSE 8000

# slim 镜像没有 curl，用标准库探活。
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import json,urllib.request,sys; r=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)); sys.exit(0 if r.get('ok') else 1)"

# 启动方式照旧：uvicorn 直接起服务。
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
