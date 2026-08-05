<template>
  <div class="login-wrap">
    <el-card class="login-card" shadow="never">
      <h1>登录</h1>
      <p class="lead muted">财务共享中台 · 本机工作台（登录后可用对话与技能）</p>

      <el-alert
        v-if="error"
        type="error"
        :title="error"
        show-icon
        :closable="false"
        style="margin: 16px 0"
        role="alert"
      />

      <el-form
        ref="formRef"
        label-position="top"
        :model="form"
        :rules="rules"
        @submit.prevent="onSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            id="username"
            v-model="form.username"
            name="username"
            autocomplete="username"
            clearable
            size="large"
            placeholder="请输入用户名"
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            id="password"
            v-model="form.password"
            name="password"
            type="password"
            autocomplete="current-password"
            show-password
            size="large"
            placeholder="请输入密码"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          native-type="submit"
          :loading="loading"
          style="width: 100%"
        >
          {{ loading ? "登录中…" : "登录" }}
        </el-button>
      </el-form>

      <div class="demo-box">
        <p><strong>本机演示账号</strong>（仅开发库，生产请关闭）</p>
        <div class="demo-row">
          <span>管理员 <code>admin</code> / <code>Phase0Demo1!</code></span>
          <el-button link type="primary" @click="fill('admin', 'Phase0Demo1!')">
            填入
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { login } from "../api/client";

const router = useRouter();
const formRef = ref(null);
const loading = ref(false);
const error = ref("");
const form = reactive({
  username: "admin",
  password: "Phase0Demo1!",
});

const rules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

function fill(u, p) {
  form.username = u;
  form.password = p;
  error.value = "";
}

async function onSubmit() {
  error.value = "";
  if (formRef.value) {
    try {
      await formRef.value.validate();
    } catch {
      return;
    }
  }
  loading.value = true;
  try {
    await login(form.username.trim(), form.password);
    ElMessage.success("登录成功");
    await router.replace({ name: "home" });
  } catch (e) {
    error.value = e.message || "登录失败，请检查用户名或密码";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.lead {
  margin: 0 0 8px;
}
</style>
