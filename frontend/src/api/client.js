/** Mid-platform API client — only talks to /api/v1 (proxied in dev). */

async function parseJson(res) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

export async function login(username, password) {
  const res = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, password }),
  });
  const data = await parseJson(res);
  if (!res.ok) {
    const err = new Error((data && data.message) || "登录失败");
    err.code = data && data.code;
    err.status = res.status;
    throw err;
  }
  return data;
}

export async function logout() {
  const res = await fetch("/api/v1/auth/logout", {
    method: "POST",
    credentials: "include",
  });
  return parseJson(res);
}

export async function fetchMe() {
  const res = await fetch("/api/v1/me", {
    credentials: "include",
  });
  const data = await parseJson(res);
  if (!res.ok) {
    const err = new Error((data && data.message) || "未登录");
    err.code = data && data.code;
    err.status = res.status;
    throw err;
  }
  return data;
}
