<template>
  <div class="card login-card">
    <h1>登录</h1>
    <p class="sub">财务共享中台 · 本机开发（Phase0）</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <form class="login-form" @submit.prevent="onSubmit">
      <div class="field">
        <label for="username">用户名</label>
        <input
          id="username"
          v-model="username"
          name="username"
          autocomplete="username"
          required
        />
      </div>
      <div class="field">
        <label for="password">密码</label>
        <input
          id="password"
          v-model="password"
          name="password"
          type="password"
          autocomplete="current-password"
          required
        />
      </div>
      <button type="submit" class="btn-primary" :disabled="loading">
        {{ loading ? "登录中…" : "登录" }}
      </button>
    </form>
    <div class="meta demo-box">
      <p><strong>本机演示账号</strong>（仅开发库）</p>
      <ul>
        <li>
          管理员
          <code>admin</code> /
          <code>Phase0Demo1!</code>
          <button type="button" class="linkish" @click="fill('admin', 'Phase0Demo1!')">
            填入
          </button>
        </li>
        <li>
          演示用户
          <code>demo</code> /
          <code>DemoUser1!</code>
          <button type="button" class="linkish" @click="fill('demo', 'DemoUser1!')">
            填入
          </button>
        </li>
        <li>
          李尚
          <code>lishang</code> /
          <code>LiShang1!</code>
          <button type="button" class="linkish" @click="fill('lishang', 'LiShang1!')">
            填入
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { login } from "../api/client";

const router = useRouter();
const username = ref("admin");
const password = ref("Phase0Demo1!");
const error = ref("");
const loading = ref(false);

function fill(u, p) {
  username.value = u;
  password.value = p;
  error.value = "";
}

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
