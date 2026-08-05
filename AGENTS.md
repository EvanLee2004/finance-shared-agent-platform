# AGENTS.md · 财务共享中台 Agent（finance-shared-agent-platform）

> 跨工具入口（agents.md 标准）。**完整铁律与模块地图以 `Agent.md` 为准。**  
> 每次开干前：先读本文件 → `Agent.md` → 工作区根 `AGENTS.md` / `Agent.md` → 下表「必读规范 / Skills」。

## 产品（一句话）

财务共享 **智能 Agent 中台**：登录后按权限使用已上架 Skills；聊天与任务均经 **原样 OpenCode**（零改 OC 源码）；管理员管账号、审批、云仓同步、审计。

## 双仓

| 仓 | 远端（优先） | 职责 |
|----|--------------|------|
| **本仓** | Gitee `Lee157/finance-shared-agent-platform` · GitHub `EvanLee2004/…` | 中台前后端、部署 |
| **skills** | Gitee `Lee157/finance-shared-skills` · GitHub `EvanLee2004/…` | 已上架公开 skill 逻辑 |

本地工作区指针：`项目/长期项目/财务Skill运行平台/`（`progress.md` = 现状 SSOT）。

## 架构（摘要）

```text
浏览器(Vue) → 中台 API(FastAPI) → 127.0.0.1 OpenCode serve
                    ↓ git 手动同步
              finance-shared-skills（仅 published）
```

- **1 用户聊天会话 = 1 OpenCode session**（上下文尊重 OC；中台做归属隔离）
- 一期可跑 skill：**仅已上架 ∩ 已授权**
- 模型：管理员配在 **OC 官方配置位**；厂商/免费模型 **完全跟 OpenCode**

## 铁律（摘要）

1. **不改 OpenCode 源码**；不浏览器直连 OC。  
2. **密钥/Key/真实财务数据不进 git**；日志脱敏。  
3. **判绿认真实退出码**：`sh tests/run_verify.sh; echo EXIT:$?`（禁止 `| tail` / `| head` 判绿）。  
4. **数字/金额不编造**；业务写系统须确认闸（后置阶段也预留）。  
5. **不碰利润看板** :80 / 8018 / 外网映射。  
6. **整洁度**：工作区 `AI开发规范/软件工程规范/代码架构与整洁度强制规范.md` + 本仓 `docs/softeng/`。  
7. **角色分离**（工作区协作）：DIRECTOR / EXECUTOR / VERIFIER / RELEASER；一 worktree 一写入者。

## 每次开干前必读

| 顺序 | 读什么 |
|------|--------|
| 0 | 本文件 + **`Agent.md`** |
| 1 | 工作区根 `AGENTS.md` → `Agent.md` → `AI开发规范/AI协作工作体系/README.md`（声明角色） |
| 2 | 项目 `progress.md` + 概要设计 `…/2_设计/02_概要设计_财务智能Agent中台.md` |
| 3 | **整洁 harness**：`AI开发规范/软件工程规范/代码架构与整洁度强制规范.md` + `docs/softeng/10_代码架构与整洁度_中台.md` |
| 4 | **作业流**：`AI开发规范/软件工程规范/软件开发默认作业流.md` |
| 5 | **失效/坑**：`AI开发规范/失效模式清单/失效模式清单_开工必读.md`（若改协作流程） |
| 6 | **Skills（方法论）**：见下节 Superpowers / 项目 skills 表 |

## Skills / Superpowers（方法论 · 非财务 skill 包）

> 财务业务 skill 在 `finance-shared-skills`；下列是 **写代码时的 AI 方法论**（Grok 插件 superpowers 等）。

| 场景 | 先读再干 |
|------|----------|
| 新功能 / 需求糊 | `brainstorming` → `writing-plans` |
| 有计划开干 | `executing-plans` / `test-driven-development`（先红后绿） |
| Bug | `systematic-debugging` |
| 收工宣称完成 | `verification-before-completion` + 本仓 `run_verify` |
| 多独立任务 | `dispatching-parallel-agents`（仍守一 worktree 一写入者） |

工作区根 `Agent.md`「Superpowers（何时用）」优先；**项目门禁与本仓铁律高于通用 skill 习惯**。

## 测试 / 门禁

```bash
# 在仓库根
sh tests/run_verify.sh; echo EXIT:$?
```

当前 scaffold 阶段：语法/结构守卫为主；功能测试随 Phase 1 增加。

## 质量工具（目标态）

- Python：ruff（`pyproject.toml`）  
- 前端：Vue 官方风格 + eslint/prettier（落地时加）  
- 密钥：gitleaks / 勿提交 `.env`  
- pre-commit：见 `.pre-commit-config.yaml`（启用后）  

## 推送

```bash
git push origin main    # GitHub
git push gitee main     # Gitee（部署优先）
```

push 前安全扫；**push 须任务授权或人确认**（工作区铁律）。
