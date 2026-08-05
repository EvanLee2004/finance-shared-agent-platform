# Agent.md — 财务共享中台 Agent（代码仓）

> **每次改本仓代码前必读本文 + `AGENTS.md`。**  
> 进度：工作区 `项目/长期项目/财务Skill运行平台/progress.md`。  
> 概要设计：工作区 `…/软件工程文档/2_设计/02_概要设计_财务智能Agent中台.md`（本仓镜像 `docs/HLD_zh.md`）。

---

## 0. 开工门闩（抄看板习惯）

1. 读工作区根 `AGENTS.md` / `Agent.md`，声明角色：`DIRECTOR | EXECUTOR | VERIFIER | RELEASER`。  
2. 读本仓 **`AGENTS.md` → 本文件**。  
3. 读项目 `progress.md` + 概要设计 / 补充拍板。  
4. **开发类**：  
   - `AI开发规范/软件工程规范/代码架构与整洁度强制规范.md`  
   - `docs/softeng/10_代码架构与整洁度_中台.md`  
   - `AI开发规范/软件工程规范/软件开发默认作业流.md`  
5. **worktree**：读 `AI开发规范/AI协作工作体系/worktree台账与开工检查.md`；项目台账见 `…/4_管理过程/worktree台账.md`；开工 `git worktree list` / `grok worktree list`。  
6. 改完：`sh tests/run_verify.sh; echo EXIT:$?` 绿后再 commit；push 须授权。

---

## 1. 这是什么

- **中台控制面**：Auth、RBAC、Skill 元数据、审批、聊天代理、审计、skills git 同步。  
- **执行**：本机 **OpenCode serve 原样**，不 fork、不改上游源码。  
- **前端**：Vue（靠拢利润看板简洁风）。  
- **一期 skill 范围**：仅 **已上架 ∩ 已授权**（私有自建对话后置）。

---

## 2. 架构

```text
Vue SPA
  → FastAPI /api/v1/*
      → Auth / Grant / SkillRegistry / ChatSession
      → OcClient ──localhost──▶ opencode serve
      → SkillsGitSync ──git──▶ finance-shared-skills (Gitee 优先)
```

| 概念 | 规则 |
|------|------|
| ChatSession | `user_id` 隔离；**1 聊 = 1 OC session** |
| 模型 | 管理员配在 OC 配置；**完全跟 OpenCode**（含免费模型） |
| 公开 skill | 只来自 published + 云仓同步；私有草稿不进公开仓 |
| 看板共机 | 独立端口；禁 :80/:8018 |

---

## 3. 目录（目标态）

```text
finance-shared-agent-platform/
├─ AGENTS.md / Agent.md      ← 开工入口
├─ docs/
│  ├─ HLD_zh.md
│  ├─ softeng/               ← 本仓整洁/架构补充
│  └─ DEPLOY_LINUX.md
├─ backend/app/              ← FastAPI
├─ frontend/                 ← Vue3+Vite（待建）
├─ deploy/linux/
├─ tests/run_verify.sh
├─ pyproject.toml            ← ruff 等
└─ skills-workspace/         ← 运行时挂载，不进 SSOT
```

---

## 4. 铁律

1. **零改 OpenCode 源码**；浏览器禁止直连 OC。  
2. **API 强制鉴权**：聊天/文件/skill 路径必须校验归属。  
3. **密钥不进 git**；`.env` / OC apiKey 仅部署机。  
4. **数字不编造**；财务写系统须人审闸（阶段到了再实现，接口预留）。  
5. **不碰利润看板** 生产入口与数据目录。  
6. **单向依赖**：route → service → repo/oc_client；UI 不算业务金额公式。  
7. **一个概念一个真相源**：Grant、Skill 状态机、catalog 版本不双轨。  
8. **判绿**：`sh tests/run_verify.sh; echo EXIT:$?`，禁 `| tail`。  
9. **先红后绿**（有行为变更时）。  
10. **文档诚实**：progress/CHANGELOG 不写未完成的「已上线」。

---

## 5. 代码整洁 harness（本仓）

正本：工作区 **`AI开发规范/软件工程规范/代码架构与整洁度强制规范.md`**。  
本仓补充：**`docs/softeng/10_代码架构与整洁度_中台.md`**。

落地工具：

- `ruff check` / `ruff format`（`pyproject.toml`）  
- `tests/run_verify.sh` 串联  
- 后续：Vue eslint、契约测试、权限越权测试  

---

## 6. Skills 表（开干场景）

| 场景 | Skill / 规范 |
|------|----------------|
| 整洁与架构 | 整洁度强制规范 + softeng/10 |
| 默认开发循环 | 软件开发默认作业流 |
| TDD | superpowers `test-driven-development` |
| Bug | `systematic-debugging` |
| 宣称完成 | `verification-before-completion` + run_verify |
| 协作角色 | AI协作工作体系 README |
| worktree | worktree台账与开工检查 |
| 财务业务 skill 内容 | **另一仓** `finance-shared-skills`，不是本表 |

---

## 7. 怎么跑（scaffold 期）

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 18000
# 健康：curl -s localhost:18000/api/v1/health
```

OpenCode：系统安装 `opencode serve`，仅 `127.0.0.1`；模型按 OC 文档配置。

门禁：

```bash
sh tests/run_verify.sh; echo EXIT:$?
```

---

## 8. 双推

```bash
git push origin main
git push gitee main
```

---

## 9. 相关路径（工作区）

| 用途 | 路径 |
|------|------|
| 项目 progress | `项目/长期项目/财务Skill运行平台/progress.md` |
| 概要设计 | `…/软件工程文档/2_设计/02_概要设计_*.md` |
| 补充拍板 | `…/2_设计/20260805_补充拍板_*.md` |
| 公开 skills 本地 | `…/程序/finance-shared-skills/` |
| 看板参考 harness | `项目/利润看板…/程序/看板正式程序/AGENTS.md` |
