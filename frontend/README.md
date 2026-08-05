# Frontend · 财务共享中台（Vue3 + Vite）

Phase0：仅登录壳（`/login` + 登录后 Home 显示用户名/角色 + 登出）。**无聊天 UI**。

## 本机开发

前置：后端已在 `127.0.0.1:18000` 运行（见仓库根 `README.md`）。

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 Vite 提示的地址（默认 `http://127.0.0.1:5173`）。

Dev 代理：`/api` → `http://127.0.0.1:18000`（见 `vite.config.js`）。

## 构建

```bash
cd frontend
npm install
npm run build
```

产物在 `frontend/dist/`（已 gitignore）。
