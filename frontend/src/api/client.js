/** Mid-platform API client — only talks to /api/v1 (proxied in dev). Never OC. */

async function parseJson(res) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

function apiError(data, fallback, status) {
  const err = new Error((data && data.message) || fallback);
  err.code = data && data.code;
  err.status = status;
  return err;
}

export async function login(username, password) {
  const res = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, password }),
  });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "登录失败", res.status);
  return data;
}

export async function logout() {
  const res = await fetch("/api/v1/auth/logout", {
    method: "POST",
    credentials: "include",
  });
  return parseJson(res);
}

export async function changePassword(oldPassword, newPassword) {
  const res = await fetch("/api/v1/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      old_password: oldPassword,
      new_password: newPassword,
    }),
  });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "修改密码失败", res.status);
  return data;
}

export async function fetchMe() {
  const res = await fetch("/api/v1/me", { credentials: "include" });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "未登录", res.status);
  return data;
}

export async function fetchDashboardStats() {
  const res = await fetch("/api/v1/dashboard/stats", { credentials: "include" });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "无法加载工作台统计", res.status);
  return data;
}

export async function fetchAdminAudit(limit = 30) {
  const res = await fetch(
    `/api/v1/admin/audit?limit=${encodeURIComponent(limit)}`,
    { credentials: "include" },
  );
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "无法加载审计日志", res.status);
  return data;
}

export async function putGrant(skillId, principalType, principalId) {
  const res = await fetch("/api/v1/admin/grants", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      skill_id: skillId,
      principal_type: principalType,
      principal_id: principalId,
    }),
  });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "授权失败", res.status);
  return data;
}

export async function fetchHealth() {
  const res = await fetch("/api/v1/health", { credentials: "include" });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "health 失败", res.status);
  return data;
}

export async function fetchOcStatus() {
  const res = await fetch("/api/v1/opencode/status", { credentials: "include" });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "探测失败", res.status);
  return data;
}

export async function fetchOcEnableGuide() {
  const res = await fetch("/api/v1/opencode/enable-guide", {
    credentials: "include",
  });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "无法加载引导", res.status);
  return data;
}

export async function fetchSkillsCatalog() {
  const res = await fetch("/api/v1/skills-catalog", { credentials: "include" });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "技能目录失败", res.status);
  return data;
}

export async function fetchSkills(scope = "runnable") {
  const res = await fetch(
    `/api/v1/skills?scope=${encodeURIComponent(scope)}`,
    { credentials: "include" },
  );
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "技能列表失败", res.status);
  return data;
}

/** Admin: sync local/Gitee skills tree (FSA_SKILLS_ROOT). */
export async function syncSkills(pull = false) {
  const res = await fetch("/api/v1/admin/skills/sync", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ pull: Boolean(pull) }),
  });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "同步技能失败", res.status);
  return data;
}

export async function listChats() {
  const res = await fetch("/api/v1/chats", { credentials: "include" });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "会话列表失败", res.status);
  return data;
}

export async function createChat(title = "新对话") {
  const res = await fetch("/api/v1/chats", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ title }),
  });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "创建会话失败", res.status);
  return data;
}

export async function listMessages(chatId, afterSeq = 0) {
  const res = await fetch(
    `/api/v1/chats/${encodeURIComponent(chatId)}/messages?after_seq=${afterSeq}`,
    { credentials: "include" },
  );
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "消息加载失败", res.status);
  return data;
}

export async function sendMessage(chatId, content, model) {
  const payload = { content };
  if (model && model.providerID && model.modelID) {
    payload.providerID = model.providerID;
    payload.modelID = model.modelID;
  }
  const res = await fetch(
    `/api/v1/chats/${encodeURIComponent(chatId)}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    },
  );
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "发送失败", res.status);
  return data;
}

/** Models from live OpenCode via mid-platform — never a local hard-coded list. */
export async function fetchOcModels() {
  const res = await fetch("/api/v1/opencode/models", { credentials: "include" });
  const data = await parseJson(res);
  if (!res.ok) throw apiError(data, "模型列表失败", res.status);
  return data;
}
