# 后续架构 Goal 草稿（≤1 页 · 可改 MASTER）

## 标题

W9.1 · 治理面补齐与配置统一（users/admin system · settings · 依赖注入）

## 背景

W9 已落实：OC 经 `oc_service`→`oc_client` 单点；api 不碰 adapter；审计/可见性枚举单点；守卫测防散落。  
未做（拍板分期）：admin users CRUD、jobs、审批流、dashboard/stats、settings 非密钥配置面。

## 目标

1. 实现设计清单 **P0 管理端用户**（开户/停用/kick）且四眼策略可选 later  
2. `GET /admin/system` 聚合 OC/skills tip/版本（无密钥）  
3. 可选：DI 容器或 FastAPI Depends 注入 OcClient，便于单测  
4. 继续保持：OC 挂中台可登录；隔离测不可删  

## 非目标

换 DB/微服务/重写前端/Gitee push

## 验收

- 接口矩阵更新；verify EXIT:0  
- 新端点有 TestClient 绿测 + 403 非 admin  

## 建议工位

同 worktree 续分支；基线 = 本 W9 tip
