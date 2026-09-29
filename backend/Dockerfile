# 基础镜像与本机要求一致：Python 3.11（补丁版本固定，见 docs/开发环境复现指南.md）
FROM python:3.11.16-slim-bookworm

# 让日志直接输出，不留在缓冲区里，便于 docker logs 排查“哪一步没过”
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/app

# 先装锁文件，依赖不变时这层走缓存；安装版本以 requirements.lock 为准（== 精确锁定）
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir -r requirements.lock

# 再拷业务代码
COPY . .

EXPOSE 8000

# 启动前自检样例数据（不依赖外部服务）：基准缺条目/指纹被改坏时直接失败并打印原因，
# 保证容器里跑出来的与本地是同一份数据；自检通过后再拉起服务（启动方式照旧）。
CMD ["sh", "-c", "python -m app.seed_cli check && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
