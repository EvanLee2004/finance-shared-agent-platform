# Architecture

## Processes

1. **platform-api** — auth, RBAC, skill metadata, approval, chat proxy, audit, skills git sync
2. **opencode serve** — unchanged upstream binary; localhost only
3. **skills git checkout** — clone of finance-shared-skills (Gitee preferred on deploy host)

## Sync

- Pull: admin button → `git pull` → validate catalog.yaml → reload mounts for OpenCode
- Push: after publish approval → write skill tree → commit → push Gitee (+ GitHub mirror)

## Sessions

`ChatSession(user_id, platform_session_id, opencode_session_id)` — never share OC sessions across users.
