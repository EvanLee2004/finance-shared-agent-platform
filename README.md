# finance-shared-agent-platform

财务共享中台 Agent：**薄控制面（Vue3 + FastAPI）+ 可选本机 [OpenCode](https://opencode.ai)**（不修改 OpenCode 源码；浏览器永不直连 OC）。

| | |
|--|--|
| 公开 Skills | [finance-shared-skills](https://github.com/EvanLee2004/finance-shared-skills) · [Gitee](https://gitee.com/Lee157/finance-shared-skills) |
| Gitee 本仓 | https://gitee.com/Lee157/finance-shared-agent-platform |
| License | MIT |
| 当前阶段 | **本机可用中台**（登录/工作台/技能同步授权/可选 OC 对话 · 一夜队列 W0–W9） |

## 架构（简 · 与代码一致）

```text
浏览器 Vue ──HTTP only──► FastAPI /api/v1
                              │
              api(薄) → services → adapters → OC / FS / SQLite
                              │
                           domain(enums/errors)

· OpenCode HTTP 仅 adapters/oc_client.py（路由经 services/oc_service）
· 权限真相在服务端（grant/admin）；前端 role 只控制展示
· OC 可选：挂时登录/health/技能目录仍可用
```

```text
浏览器 → 中台 Vue (127.0.0.1:5173) → 中台 API (127.0.0.1:18000)
                                         ├─ SQLite data/app.db
                                         └─ 可选 → 127.0.0.1:4096 OpenCode serve
```

| 能力 | 是否需要 OpenCode |
|------|-------------------|
| 登录 / 工作台 / health / 主题 / 技能目录 / 授权治理 | **否** |
| 智能对话发消息 / 模型列表 | **是**（可先建会话、浏览历史；模型来自 OC API 全量列表） |

Skills 来源：本机 `FSA_SKILLS_ROOT`（或默认探测到的 `finance-shared-skills` 克隆）→ `catalog.yaml` 同步入库；**published ∩ 授权** 可运行（admin 默认可跑全部 published）。公开仓：[Gitee finance-shared-skills](https://gitee.com/Lee157/finance-shared-skills)。

- 1 中台 chat 会话 ↔ 1 OpenCode session（有 OC 时绑定）
- 模型 API Key **只在 OpenCode 侧**配置，禁止进 git
- 消息发送：**同步**等待 OC 回复（MVP）；错误以人话展示

## 目录

```text
backend/     FastAPI（api / services / db / adapters / domain）
frontend/    Vue3 + Vite 工作台
deploy/      Linux 脚本
docs/        架构与验收证据
tests/       门禁与 pytest
data/        本地 SQLite（gitignore）
```

## 本机一键跑（中台）

仓库根目录示例（绝对路径按本机 worktree 调整）：

```bash
cd /path/to/finance-shared-agent-platform

export FSA_DATA_ROOT="$(pwd)/data"
export FSA_BOOTSTRAP_ADMIN_USER=admin
export FSA_BOOTSTRAP_ADMIN_PASSWORD='Phase0Demo1!'
export FSA_OPENCODE_BASE_URL=http://127.0.0.1:4096
# 可选：本地 finance-shared-skills 克隆路径（管理员可 POST /api/v1/admin/skills/sync）
# export FSA_SKILLS_ROOT=/path/to/finance-shared-skills

cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 18000
```

另开终端：

```bash
cd /path/to/finance-shared-agent-platform/frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

浏览器：`http://127.0.0.1:5173/login`  
演示账号（首次无 admin 时 bootstrap）：`admin` / `Phase0Demo1!`

### 自检

```bash
curl -sS http://127.0.0.1:18000/api/v1/health
```

## 可选：OpenCode serve

中台 **不会**静默安装。请在工作台点「启用 OpenCode」确认后，按界面可复制命令在本机执行。常用：

```bash
which opencode && opencode --version
opencode upgrade
opencode serve --port 4096 --hostname 127.0.0.1
```

探测：

```bash
curl -sS http://127.0.0.1:4096/global/health || curl -sS http://127.0.0.1:4096/
```

回到工作台点「我已启动」重新探测。

## 前端页面

| 路由 | 说明 |
|------|------|
| `/login` | 登录 |
| `/` | 工作台（用户、health、OC 状态、入口卡片） |
| `/chats` | 智能对话 |
| `/skills` | 技能目录只读 |

顶栏可切换 **Light / Neon** 主题（`localStorage` 键 `fsa_theme`）。

## 门禁

```bash
sh tests/run_verify.sh; echo EXIT:$?
```

须 `EXIT:0`。

## 安全

- 密码 Argon2id；Cookie `fsa_sid` HttpOnly；库存 token SHA-256
- 仅 `backend/app/adapters/oc_client.py` 访问 OpenCode
- 请勿提交 `.env`、API Key、真实财务数据
