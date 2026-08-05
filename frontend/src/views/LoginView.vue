<template>
  <div class="card">
    <h1>登录</h1>
    <p class="sub">财务共享中台 · 本机开发</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <form @submit.prevent="onSubmit">
      <label for="username">用户名</label>
      <input
        id="username"
        v-model="username"
        autocomplete="username"
        required
      />
      <label for="password">密码</label>
      <input
        id="password"
        v-model="password"
        type="password"
        autocomplete="current-password"
        required
      />
      <button type="submit" :disabled="loading">
        {{ loading ? "登录中…" : "登录" }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { login } from "../api/client";

const router = useRouter();
const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

async function onSubmit() {
  error.value = "";
  loading.value = true;
  try {
    await login(username.value.trim(), password.value);
    await router.replace({ name: "home" });
  } catch (e) {
    error.value = e.message || "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>
