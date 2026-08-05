# finance-shared-agent-platform

财务共享中台 Agent：**薄控制面（Vue + FastAPI）+ 原样 [OpenCode](https://opencode.ai)**（不修改 OpenCode 源码）。

| | |
|--|--|
| 公开 Skills | [finance-shared-skills](https://github.com/EvanLee2004/finance-shared-skills) · [Gitee](https://gitee.com/Lee157/finance-shared-skills) |
| Gitee 本仓 | https://gitee.com/Lee157/finance-shared-agent-platform |
| License | MIT |

## 架构（简）

```text
浏览器 → 本仓 API → 127.0.0.1 OpenCode serve
              ↓ 手动同步
     finance-shared-skills
```

- 1 聊天会话 ↔ 1 OpenCode session  
- 一期：仅已上架且授权的 skill  
- 模型：在 OpenCode 官方配置中管理（含免费模型）

## 目录

```text
backend/     FastAPI
frontend/    Vue（建设中）
deploy/      Linux 脚本
docs/        架构与部署说明
tests/       门禁与测试
```

## 本地（scaffold）

```bash
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 18000
curl -s http://127.0.0.1:18000/api/v1/health
```

```bash
sh tests/run_verify.sh; echo EXIT:$?
```

## 文档

- [架构](docs/ARCHITECTURE.md)
- [Linux 部署要点](docs/DEPLOY_LINUX.md)
- [概要设计（中文）](docs/HLD_zh.md)

## 安全

请勿提交 `.env`、API Key、真实财务数据。见 `.gitignore`。
