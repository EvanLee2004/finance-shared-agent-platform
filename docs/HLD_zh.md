# 概要设计 · 财务智能 Agent 中台

| 项 | 内容 |
|----|------|
| **文档编号** | HLD-FSA-001 |
| **版本** | **v0.1** |
| **日期** | 2026-08-05 |
| **状态** | 已按拍板成文 · 可供拆任务开工 |
| **产品名** | 财务共享中台 Agent / 财务智能 Agent 中台 |
| **英文仓** | `finance-shared-agent-platform` + `finance-shared-skills` |

**依据文档（同项目 `方案与文档/`）：**

- `20260805_双仓开源与Skills同步架构.md`  
- `20260805_产品蓝图_做出来长什么样.md`  
- `20260805_最佳架构与业务流程图.md`  
- `20260805_阶段判定与待拍板清单.md`  
- `1_需求/01_需求说明_MVP与成功标准.md`  

**相关开源仓：**

| 用途 | GitHub | Gitee（部署优先） |
|------|--------|-------------------|
| 平台 | https://github.com/EvanLee2004/finance-shared-agent-platform | https://gitee.com/Lee157/finance-shared-agent-platform |
| Skills | https://github.com/EvanLee2004/finance-shared-skills | https://gitee.com/Lee157/finance-shared-skills |

**参考实现（不作为主线仓）：** `ErenYeager2002/financial_pj` / 本地 `程序/financial_pj`

---

## 1. 目标与非目标

### 1.1 目标

1. 财务共享式 **统一入口**：登录后按权限使用 Skills，降低 OpenCode/环境门槛。  
2. **最大程度使用 OpenCode 能力**：标准任务与聊天均经 OC 执行；**零修改 OC 源码**。  
3. **Skills 可治理**：自建自用、上架审批（摘要+diff）、多对多授权、与公开 git 仓手动同步。  
4. **可审计、可部署**：管理员管账号；全量业务/治理日志；Linux 部署机与看板隔离端口。  
5. **开源可协作**：平台与公开 skills 双仓、GitHub+Gitee，便于与李尚协作及国内部署拉取。

### 1.2 非目标

| 不做 | 原因 |
|------|------|
| Fork / 改 OpenCode | 升级与安全成本；官方能力最大化 |
| 浏览器直连 OC | 越权与会话串扰风险 |
| 用户免审改公共库 | 知识复用必须可审 |
| 与看板共用 DB/账号文件 | 故障域隔离 |
| 占看板 :80 / 外网映射 | 生产红线 |
| 一次交付「永久完美」所有增强 | DoD 列全、**分期排序**交付 |

### 1.3 设计原则（避免以后麻烦）

1. **双进程**：中台控制面 ≠ OpenCode 运行时。  
2. **双仓**：产品代码 ≠ 公开 skill 资产。  
3. **1 聊 1 OC session**：上下文交给 OC；隔离与鉴权交给中台。  
4. **Job/运行钉扎 skill 版本**：pull 云仓不改在跑任务。  
5. **密钥与数据不进 git**；日志脱敏。  
6. **部署机可更新 OC**；开发者电脑不能翻墙不阻塞（离线包/Gitee）。  

---

## 2. 用户与角色

| 角色 | 权限摘要 |
|------|----------|
| **user** | 登录；跑授权 skill；自己的聊天与运行记录；创建/编辑**私有** skill 并自测 |
| **creator** | 同 user；可提交上架/变更申请（可与 user 合并，用权限点区分） |
| **admin** | 用户开户改密；审批 diff；归属与授权；云仓拉/推；全站日志；系统与 OC 版本操作 |

MVP 可实现为三角色或「user + admin」+ 权限点 `skill:publish_request`。

**运维权与业务审批权**：admin 默认可审批上架；未来「写账确认」可单独授权，避免「运维=自动财务终审」。

---

## 3. 逻辑架构

```text
┌──────────────────────────────────────────────────────────┐
│ 浏览器 · 简洁 UI（风格靠拢利润看板）                        │
│ 登录 | 工作台 | 可运行 | 聊天 | 我的 Skill | 管理端         │
└────────────────────────────┬─────────────────────────────┘
                             │ 仅访问中台（内网 URL）
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 中台 API · finance-shared-agent-platform                 │
│ Auth · RBAC · SkillMeta · Approval · ChatProxy · Audit   │
│ SkillsGitSync · OcClient · FileStore · UserAdmin         │
└───────────────┬──────────────────────────┬───────────────┘
                │ 127.0.0.1 回环            │ git（部署机）
                ▼                          ▼
┌───────────────────────────┐  ┌───────────────────────────┐
│ OpenCode Server（原样）    │  │ finance-shared-skills     │
│ session / agent / skills  │  │ Gitee 优先 · GitHub 镜像  │
│ 不改源码 · 版本钉死        │  │ 仅已上架公开包             │
└───────────────────────────┘  └───────────────────────────┘
```

### 3.1 分层职责

| 层 | 职责 | 不负责 |
|----|------|--------|
| 前端 | 降门槛交互、展示进度与结果 | 直连 OC、存密钥 |
| 中台 API | 人、权、元数据、审批、会话映射、审计、挂载 skill、调 OC | 复刻 OC 上下文引擎 |
| OpenCode | 理解、选 skill、工具调用、多轮上下文 | 部门账号体系 |
| Skills 仓 | 公开能力版本 SSOT | 私有草稿、运行产物 |

---

## 4. 模块划分

| 模块 | 说明 | 优先级 |
|------|------|--------|
| **M1 Auth** | 登录会话、密码哈希、管理员 CRUD 用户、改密踢会话 | P0 |
| **M2 RBAC / Grant** | 角色；Skill↔User/Role 多对多；列表过滤 | P0 |
| **M3 Skill 生命周期** | 私有 / 待审 / 已上架 / 停用；摘要+diff 审批 | P0 |
| **M4 SkillsGitSync** | 配置远端（默认 Gitee）；拉取；推送已上架；catalog 校验 | P0 |
| **M5 OcRuntime** | 封装 `opencode serve` HTTP；健康检查；版本号读取 | P0 |
| **M6 Chat** | ChatSession↔oc_session 1:1；消息转发；按 user 隔离 | P0 |
| **M7 TaskRun** | 可选「任务卡片」一键跑指定 skill（仍经 OC） | P0 |
| **M8 Files** | 上传/下载；每会话或每 Job 独立目录 | P0 |
| **M9 Audit** | 登录、运行、同步、授权、审批、用户变更全记录 | P0 |
| **M10 Admin UI** | 用户、审批队列、授权、同步按钮、日志、OC 更新入口 | P0 |
| **M11 OcUpdate** | 部署机钉版本安装/回滚脚本；管理端触发（受控） | P1 |
| **M12 Creator UX** | 向导建 skill、编辑器简化 | P1（可用上传包+元数据先顶） |
| **M13 通知** | 站内「待审批」角标 | P2 |
| **M14 SSO** | 飞书/企微 | 以后 |

### 4.1 与 `financial_pj` 复用策略

| 可参考/移植 | 宜重做 |
|-------------|--------|
| Registry/清单扫描思路 | 演示 Header 身份 → 真登录 |
| Run 状态与产物存储概念 | Worker 直跑 skill → **OcClient** |
| Workflow 对话页交互 | 会话模型改为绑 OC session |
| 文件上传与隔离目录 | 产品信息架构（工作台/审批/同步） |
| 测试与目录习惯 | 看板风 UI（可 Vue 对齐看板） |

**结论**：主线在 **新仓** 实现；`financial_pj` 作对照实现，不强制合并历史包袱。

---

## 5. 关键业务流程

### 5.1 登录与工作台

```text
登录 → 会话 Cookie
  → 首页：Skill 总数 | 我的 Skill 数 | 入口（可运行 / 聊天 / 我的 Skill / 管理）
```

### 5.2 聊天（智能小任务）

```text
用户新建/打开 ChatSession（仅本人可见）
  → 中台创建或恢复 OpenCode session（绑定 user_id）
  → 用户发消息/附件 → 中台写入文件目录 → 转发 OC
  → OC 回复/工具结果 → 中台落库展示
  → 上下文压缩与历史：尊重 OC；中台只存展示与审计所需
```

**硬规则：** 任何 Chat API 必须校验 `session.user_id == 当前用户`（admin 审计另议）。

### 5.3 Skill 自建 → 上架

```text
创建/编辑私有 Skill（磁盘：data/private/{user_id}/skills/...）
  → 自测：挂到本人 OC 可见路径或会话工作区
  → 提交上架/变更
  → 管理员：摘要 + diff（相对当前已上架版或空）
  → 批准 → 状态=已上架；进入「可同步云仓」集合
  → 驳回 → 仍私有
```

### 5.4 授权（已上架）

```text
管理员：Grant(skill_id, user|role)
  → 用户「可运行」列表 = 已上架 ∩ 授权 ∪ 本人私有
  → UI：矩阵或拖拽（MVP 可用穿梭框，模型先多对多）
```

### 5.5 云仓同步（手动一点）

| 操作 | 行为 |
|------|------|
| **拉取** | `git pull`（Gitee）→ 校验 catalog.yaml → 更新本地公开 skill 树 → 审计 |
| **推送** | 将**已批准上架**的 skill 写入 skills 工作树 → 更新 catalog → commit → push Gitee（+ 可选 origin GitHub） |

**私有与待审永不 push。**  
**进行中的 Chat/Job 钉扎 skill 内容哈希或版本，不因 pull 改写。**

### 5.6 OpenCode 更新（部署机）

```text
钉版本 vX.Y.Z → 下载 release 或离线包 → sha256
  → /opt/opencode/versions/vX.Y.Z
  → 切换 current 软链 → restart serve → health
  → 失败回滚上一版本
```

开发者 Mac 不翻墙：**不在本机装生产 OC**；更新脚本只在部署机执行。

---

## 6. 数据概念模型（概要级）

```text
User(id, username, password_hash, role, status, ...)
Session(token, user_id, expires_at)

Skill(
  id, owner_id, visibility,   -- private | pending | published | disabled
  version, content_hash, summary, risk_level, path
)
SkillRevision(skill_id, version, diff_meta, submitted_by, reviewed_by, status)

Grant(skill_id, principal_type, principal_id, perm)  -- run | ...

ChatSession(id, user_id, title, opencode_session_id, work_dir, created_at)
ChatMessage(id, chat_id, role, content_ref, created_at)

Job(id, user_id, skill_id, skill_version, skill_hash, status, ...)  -- 可选任务卡片

AuditEvent(id, actor_id, action, target, detail_json, created_at)

SystemConfig(skills_repo_url, skills_repo_branch, opencode_endpoint, ...)
```

存储：MVP **SQLite**（单机）；并发与备份策略在详细设计/运维说明；推广前评估 PostgreSQL。

---

## 7. 接口轮廓（非字段级详细设计）

| 前缀 | 用途 |
|------|------|
| `POST /api/v1/auth/login` `logout` | 登录登出 |
| `GET /api/v1/me` `GET /api/v1/dashboard/stats` | 我、首页数字 |
| `GET /api/v1/skills` | 可见列表（过滤授权+私有） |
| `POST /api/v1/skills` `PATCH ...` | 创建/改私有 |
| `POST /api/v1/skills/{id}/submit` | 提交审批 |
| `GET /api/v1/admin/approvals` `POST .../approve|reject` | 审批 |
| `PUT /api/v1/admin/grants` | 授权 |
| `GET/POST /api/v1/chats` `.../messages` | 聊天 |
| `POST /api/v1/admin/skills/sync/pull` `.../push` | 云仓同步 |
| `GET /api/v1/admin/audit` | 审计 |
| `GET /api/v1/admin/users` CRUD | 用户 |
| `GET /api/v1/health` | 含 OC/skills 粗状态 |

浏览器 **禁止** 配置 OC 直连地址。

---

## 8. 前端信息架构

```text
/login
/                   工作台（总数 / 我的 / 快捷入口）
/skills             可运行（卡片）
/chats              会话列表
/chats/:id          单会话（一框 = 一 OC session）
/my/skills          我的 skill（私有/待审/已上架）
/admin/users
/admin/approvals
/admin/grants
/admin/sync
/admin/audit
/admin/system       OC 版本、健康、限额说明
```

视觉：**简洁、靠拢利润看板**（字体层级、主色、登录与顶栏节奏）；实现可选 Vue（更易抄看板）或 React（抄 financial_pj），**概要不锁死框架**，开工前由实现人选定一种。

---

## 9. 部署架构

```text
内网浏览器
  → http(s)://部署机:独立端口（如 18080）反代
  → 127.0.0.1:平台 API
  → 127.0.0.1:OpenCode serve

/opt/finance-shared/
  platform/          平台发布
  skills-repo/       finance-shared-skills 检出（Gitee）
  data/              DB、私有 skill、上传、日志
/opt/opencode/versions/<ver> + current
```

| 红线 | 说明 |
|------|------|
| 不监听/不改看板 :80 | 外网映射依赖 |
| 不占 8018 | 看板 app |
| cgroup 限额 | MemoryMax/CPUQuota/任务并发 |
| OC 仅 127.0.0.1 | 不暴露内网 |

与看板 **同机可试点**；正式高负载或写系统增多时评估专机。

---

## 10. 安全设计（概要）

| 项 | 要求 |
|----|------|
| 密码 | 哈希存储；管理员可重置；传输 HTTPS 或内网可信 |
| 会话 | HttpOnly Cookie；超时；改密作废 |
| 授权 | 每次 API 服务端校验，不信前端隐藏 |
| 文件 | 路径规范化；禁 `..`；按 user/session 分目录 |
| OC 工具 | 默认 deny；仅任务目录与白名单 skill |
| 密钥 | 模型 Key 等加密落库；不进 Audit 明文 |
| 开源 | 无生产配置、无真实 xlsx、无 token |

---

## 11. Skills 仓约定

- 路径：`skills/<id>/` + 根 `catalog.yaml`  
- 禁止：工作区、config.local、真实批量数据、密钥  
- 批准上架后：`version` + `content_hash` 更新 catalog  
- 导出脚本：`finance-shared-skills/scripts/export_from_finance_skills.sh`（从旧 monorepo 脱敏）  

历史仓 `EvanLee2004/finance-skills` 可继续开发；**中台公开库 SSOT = finance-shared-skills**。

---

## 12. 分期与里程碑（DoD 全开 · 只排序）

### Phase 0 · 基线（约 1 周）

- 仓库与部署目录规范、健康检查  
- 配置：skills 远端、OC endpoint  
- 从 scaffold 拉通 `health` + 静态前端壳  

### Phase 1 · 可登录可聊可跑（MVP 核心）

- M1 Auth + 管理员开户  
- M5 OcRuntime + M6 Chat（隔离）  
- M3 私有 skill + 本地挂载给本人  
- M8 文件 + M9 基础审计  
- 前端：登录、工作台数字、聊天、我的 skill  

### Phase 2 · 共享治理

- 审批 diff、已上架、M2 授权  
- M4 拉/推 Gitee（+ GitHub 可选）  
- 管理端审批/授权/同步/审计页  

### Phase 3 · 体验与运维

- 任务卡片一键跑  
- 看板风 UI 打磨  
- M11 OC 一键更新/回滚  
- 配额与备份 SOP、试点  

### Phase 4 · 扩展

- 高风险确认闸（写表类）  
- SSO、通知、PG 等  

---

## 13. 风险与对策

| 风险 | 对策 |
|------|------|
| OC API/行为随版本变 | 钉版本；升级走测试+回滚 |
| 会话串权 | 强制 user_id 校验；集成测试 |
| 误推私有 skill 到公网 | 推送白名单=已上架；CI/脚本校验 .gitignore |
| 与看板抢资源 | 限额、独立端口、监控 |
| 范围膨胀 | 概要分期；完美主义只排序 |
| 双仓不同步 | 管理端显示双方 tip；手动同步按钮 |

---

## 14. 测试策略（概要）

| 层 | 内容 |
|----|------|
| 单元 | 授权过滤、路径安全、catalog 解析 |
| 集成 | 登录→聊天→OC mock 或测试实例；审批→push dry-run |
| 安全 | 越权读他人 chat/文件；未登录访问 |
| 部署 | health；与看板端口并存冒烟 |
| 验收 | 需求文档成功标准 |

详细用例进 `3_测试/`（施工时补）。

---

## 15. 协作与分支

| 角色 | 职责 |
|------|------|
| 明昊 | 产品口径、验收、skill 业务、陆总沟通 |
| 李尚 | 平台实现、部署、OC 接入、同步脚本 |

- 平台仓：`main` 稳定；`feature/*` PR  
- Skills 仓：批准内容进 `main`；大改 PR  
- 本地工作区：`项目/长期项目/财务Skill运行平台/`  

---

## 16. 开放问题（不阻塞 v0.1 开工）

| # | 问题 | 默认 |
|---|------|------|
| 1 | 前端 Vue vs React | 实现时二选一，优先看谁主写 |
| 2 | 陆总试点名单 | 上线前确认 |
| 3 | 高风险写表是否进 Phase 3 | 默认确认闸设计预留，实现后置 |
| 4 | Gitee 是否给李尚 write | 建议给 |

---

## 17. 文档修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.1 | 2026-08-05 | 首版概要设计：双仓、壳+OC、会话隔离、上架审批、同步、分期 |

---

## 18. 下一步（工程）

1. 李尚接受 GitHub 邀请；对齐本概要。  
2. 在 `finance-shared-agent-platform` 开 `feature/phase1-auth-chat`：Auth + Chat + OcClient。  
3. 详细设计（可选薄）：会话表字段、OC API 映射表、审批 diff 算法。  
4. 部署机：装钉版 OC、clone skills（Gitee）、反代端口规划。  

**本概要设计批准后即可按 Phase 0→1 开工。**
