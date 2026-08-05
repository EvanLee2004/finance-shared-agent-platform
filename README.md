# finance-shared-agent-platform

财务共享中台 Agent：**薄控制面（Vue3 + FastAPI）+ 原样 [OpenCode](https://opencode.ai)**（不修改 OpenCode 源码）。

| | |
|--|--|
| 公开 Skills | [finance-shared-skills](https://github.com/EvanLee2004/finance-shared-skills) · [Gitee](https://gitee.com/Lee157/finance-shared-skills) |
| Gitee 本仓 | https://gitee.com/Lee157/finance-shared-agent-platform |
| License | MIT |
| 当前阶段 | **Phase0 地基**（Schema v1 + 登录 + health + Vue 登录壳） |

## 架构（简）

```text
浏览器 → 本仓 API (127.0.0.1:18000) → 127.0.0.1 OpenCode serve
              ↓ 手动同步
     finance-shared-skills
```

- 1 聊天会话 ↔ 1 OpenCode session（Phase1+）
- 一期：仅已上架且授权的 skill
- 模型：在 OpenCode 官方配置中管理（含免费模型）

## 目录

```text
backend/     FastAPI（api / services / db / adapters / domain）
frontend/    Vue3 + Vite 登录壳
deploy/      Linux 脚本
docs/        架构与部署说明 · 验收证据
tests/       门禁与 pytest
data/        本地 SQLite（gitignore · 默认 FSA_DATA_ROOT）
```

## 本机运行（Phase0）

### 1. 后端

在仓库根目录：

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

首次启动可种子管理员（**仅当库中尚无 admin**）：

```bash
export FSA_BOOTSTRAP_ADMIN_USER=admin
export FSA_BOOTSTRAP_ADMIN_PASSWORD='change-me-now'
# 可选：数据目录（默认：仓库旁 data/）
# export FSA_DATA_ROOT=/absolute/path/to/data
# 可选：OpenCode 探测地址（默认 http://127.0.0.1:4096）
# export FSA_OPENCODE_BASE_URL=http://127.0.0.1:4096
```

启动 API：

```bash
cd backend
. .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 18000
```

自检：

```bash
curl -s http://127.0.0.1:18000/api/v1/health
curl -s -c /tmp/fsa_cookie.txt -X POST http://127.0.0.1:18000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"change-me-now"}'
curl -s -b /tmp/fsa_cookie.txt http://127.0.0.1:18000/api/v1/me
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 Vite 输出的地址（默认 `http://127.0.0.1:5173`）。  
开发代理：`/api` → `http://127.0.0.1:18000`（见 `frontend/vite.config.js`）。

页面：`/login` → 登录后 Home 显示用户名与 role → 登出。**无聊天 UI**。

### 3. 门禁

在仓库根：

```bash
sh tests/run_verify.sh; echo EXIT:$?
```

须得到 `EXIT:0`（含 secrets 检查、compileall、pytest；有 npm 时含 frontend build）。

## 安全

- 密码：Argon2id；会话 Cookie `fsa_sid`（HttpOnly）；库中仅存 token 的 SHA-256
- 请勿提交 `.env`、API Key、真实财务数据。见 `.gitignore`（含 `data/`）
- 仅 `backend/app/adapters/oc_client.py` 可访问 OpenCode；浏览器不直连 OC

## 文档

- [架构](docs/ARCHITECTURE.md)
- [Linux 部署要点](docs/DEPLOY_LINUX.md)
- [概要设计（中文）](docs/HLD_zh.md)
- [Phase0 验收证据](docs/验收证据/phase0/)
