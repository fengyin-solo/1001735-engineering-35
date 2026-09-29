# 基础镜像与本机要求一致：Node 20.20.2 / Alpine 3.22（版本固定，见开发文档）
FROM node:20.20.2-alpine3.22

WORKDIR /srv/web

# 依赖版本以 package-lock.json 为准：npm ci 严格按锁文件安装，锁与 package.json
# 不一致会直接失败（而不是悄悄改版本），保证本地与容器装出同一棵 node_modules
COPY package.json package-lock.json ./
RUN npm ci

# 再拷业务代码
COPY . .

EXPOSE 5173

# 容器里需要对 0.0.0.0 监听，端口映射到宿主机后照旧访问 127.0.0.1:5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
