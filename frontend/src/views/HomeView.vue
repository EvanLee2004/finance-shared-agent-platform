<template>
  <div class="card">
    <h1>首页</h1>
    <p class="sub">已登录 · Phase0 无聊天 UI</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div v-if="user" class="meta">
      <div>用户名：<strong>{{ user.username }}</strong></div>
      <div>角色：<strong>{{ user.role }}</strong></div>
      <div v-if="user.display_name">
        显示名：<strong>{{ user.display_name }}</strong>
      </div>
    </div>
    <div class="row" style="margin-top: 1.25rem">
      <button class="secondary" type="button" @click="onLogout">登出</button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { fetchMe, logout } from "../api/client";

const router = useRouter();
const user = ref(null);
const error = ref("");

onMounted(async () => {
  try {
    const data = await fetchMe();
    user.value = data.user;
  } catch {
    await router.replace({ name: "login" });
  }
});

async function onLogout() {
  try {
    await logout();
  } catch {
    /* still leave */
  }
  await router.replace({ name: "login" });
}
</script>
