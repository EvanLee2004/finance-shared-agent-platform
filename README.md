# finance-shared-agent-platform

**财务共享中台 Agent** — 薄控制面 + 原样 [OpenCode](https://opencode.ai) 运行时。

| 项 | 说明 |
|----|------|
| 改 OpenCode 源码？ | **否**，只调用 `opencode serve` |
| Skills 公开库 | 独立仓 [finance-shared-skills](https://github.com/EvanLee2004/finance-shared-skills) |
| 产品 | 登录、权限、任务/聊天、Skill 上架审批、与云仓一键同步 |
| 部署 | Linux 部署机；Skills 优先 Gitee（国内） |

## 架构（摘要）

```text
浏览器 → 中台 API（本仓）→ 127.0.0.1 OpenCode Server
                ↓
     finance-shared-skills（git pull/push 手动同步）
```

- 1 用户聊天会话 ↔ 1 OpenCode session
- 未上架 Skill 仅自用；管理员批准后可授权并同步到 skills 仓

## License

MIT
