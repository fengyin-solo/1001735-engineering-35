# 前端镜像：依赖以 package-lock.json 为准（npm ci 严格按锁安装），
# 基础镜像钉到 manifest 摘要，保证任何机器构建结果一致。
# 摘要对应 docker.io/library/node:20-alpine（多架构 manifest list）。
FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293

WORKDIR /srv/web

# npm ci 要求 package.json 与 package-lock.json 同时存在，且严格按锁文件安装。
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# 开发态起 vite dev server，监听全部网卡以便容器端口映射；
# 镜像内 /api 的代理目标由 VITE_PROXY_TARGET 注入（compose 指向 http://backend:8000）。
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
