<template>
  <div class="workbench">
    <h1>工作台</h1>
    <p class="sub">
      中台可独立使用；OpenCode 为可选增强。浏览器只访问中台 API，永不直连 OC。
    </p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <div class="grid">
      <section class="panel">
        <h2>当前用户</h2>
        <p v-if="user" class="meta-line">
          用户名：<strong>{{ user.username }}</strong>
        </p>
        <p v-if="user" class="meta-line">
          角色：<strong>{{ user.role }}</strong>
        </p>
        <p v-if="user?.display_name" class="meta-line">
          显示名：<strong>{{ user.display_name }}</strong>
        </p>
        <div class="row" style="margin-top: 0.85rem">
          <button class="secondary" type="button" @click="onLogout">登出</button>
        </div>
      </section>

      <section class="panel">
        <h2>中台状态</h2>
        <p class="meta-line">
          Health：
          <span class="chip" :class="health?.status === 'ok' ? 'ok' : 'off'">
            {{ health?.status || "…" }}
          </span>
        </p>
        <p class="meta-line">
          Schema：<strong>{{ health?.schema_version ?? "—" }}</strong>
        </p>
        <p class="meta-line">
          数据库：
          <span class="chip" :class="health?.db?.ok ? 'ok' : 'off'">
            {{ health?.db?.ok ? "可用" : "异常" }}
          </span>
        </p>
      </section>

      <section class="panel">
        <h2>OpenCode（可选）</h2>
        <p class="meta-line">
          状态：
          <span class="chip" :class="ocOnline ? 'ok' : 'off'">
            {{ ocOnline ? "在线" : "离线" }}
          </span>
        </p>
        <p class="meta-line">
          探测：<strong>{{ health?.opencode?.endpoint || "—" }}</strong>
        </p>
        <p class="meta-line">
          版本：<strong>{{ health?.opencode?.version || "未知" }}</strong>
        </p>
        <p v-if="!ocOnline && health?.opencode?.error" class="meta-line">
          原因：{{ health.opencode.error }}
        </p>
        <div class="row" style="margin-top: 0.75rem">
          <button v-if="!ocOnline" type="button" @click="openOcGuide">
            启用 OpenCode
          </button>
          <button class="secondary" type="button" @click="refreshHealth">
            重新探测
          </button>
        </div>
        <p v-if="probeMsg" class="ok-msg" style="margin-top: 0.5rem">
          {{ probeMsg }}
        </p>
      </section>
    </div>

    <h2 style="margin: 1.5rem 0 0.75rem; font-size: 1.1rem">入口</h2>
    <div class="grid">
      <button class="entry" type="button" @click="goChat">
        <h3>智能对话</h3>
        <p class="hint">
          依赖本机 OpenCode serve。可先建会话、浏览历史；发送消息需 OC 在线。
        </p>
      </button>
      <button class="entry" type="button" @click="showCaps = !showCaps">
        <h3>本机能力说明</h3>
        <p class="hint">哪些不依赖 OC、哪些依赖 OC（诚实说明）。</p>
      </button>
      <button class="entry" type="button" @click="goSkills">
        <h3>技能目录（只读）</h3>
        <p class="hint">本地说明项；业务 skill 上架授权见后续 Phase。</p>
      </button>
    </div>

    <section v-if="showCaps" class="panel" style="margin-top: 1rem">
      <h2>能力边界</h2>
      <ul class="honest-list">
        <li>
          <strong>不依赖 OC</strong>：登录/登出、工作台、health、主题切换、技能目录只读、会话列表与历史浏览
        </li>
        <li>
          <strong>依赖 OC</strong>：智能对话发送消息、模型推理（Key 在 OC 侧配置，永不进 git）
        </li>
        <li>中台不会静默安装软件；启用 OC 需你确认并在本机执行命令</li>
      </ul>
    </section>

    <!-- OC enable modal -->
    <div
      v-if="showGuide"
      class="modal-backdrop"
      role="dialog"
      aria-modal="true"
      @click.self="showGuide = false"
    >
      <div class="modal">
        <h2>{{ guide?.title || "启用 OpenCode" }}</h2>
        <p>{{ guide?.summary }}</p>

        <template v-if="!confirmed">
          <p style="margin-top: 0.75rem">
            <strong>二次确认</strong>：{{ guide?.confirm_text }}
          </p>
          <div class="row" style="margin-top: 1rem">
            <button type="button" @click="confirmed = true">我确认，查看命令</button>
            <button class="secondary" type="button" @click="showGuide = false">
              取消
            </button>
          </div>
        </template>

        <template v-else>
          <div v-for="(c, i) in guide?.commands || []" :key="i">
            <p class="meta-line"><strong>{{ c.label }}</strong></p>
            <pre class="cmd-block">{{ c.cmd }}</pre>
            <button class="secondary" type="button" @click="copyCmd(c.cmd)">
              复制
            </button>
          </div>
          <p style="margin-top: 0.75rem">{{ guide?.after_start }}</p>
          <p class="sub" style="margin-top: 0.5rem">排查：</p>
          <ul class="honest-list">
            <li v-for="(t, i) in guide?.troubleshooting || []" :key="i">{{ t }}</li>
          </ul>
          <div class="row" style="margin-top: 1rem">
            <button type="button" :disabled="probing" @click="onIStarted">
              {{ probing ? "探测中…" : "我已启动" }}
            </button>
            <button class="secondary" type="button" @click="showGuide = false">
              关闭
            </button>
          </div>
          <p v-if="probeMsg" :class="ocOnline ? 'ok-msg' : 'error'" style="margin-top: 0.65rem">
            {{ probeMsg }}
          </p>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  fetchHealth,
  fetchMe,
  fetchOcEnableGuide,
  fetchOcStatus,
  logout,
} from "../api/client";

const router = useRouter();
const route = useRoute();
const user = ref(null);
const health = ref(null);
const error = ref("");
const showCaps = ref(false);
const showGuide = ref(false);
const confirmed = ref(false);
const guide = ref(null);
const probing = ref(false);
const probeMsg = ref("");

const ocOnline = computed(() => Boolean(health.value?.opencode?.ok));

onMounted(async () => {
  try {
    const me = await fetchMe();
    user.value = me.user;
    await refreshHealth();
    if (route.query.oc === "1") {
      await openOcGuide();
    }
  } catch {
    await router.replace({ name: "login" });
  }
});

async function refreshHealth() {
  try {
    health.value = await fetchHealth();
  } catch (e) {
    error.value = e.message || "无法加载 health";
  }
}

async function openOcGuide() {
  confirmed.value = false;
  probeMsg.value = "";
  try {
    guide.value = await fetchOcEnableGuide();
    showGuide.value = true;
  } catch (e) {
    error.value = e.message || "无法加载引导";
  }
}

async function onIStarted() {
  probing.value = true;
  probeMsg.value = "";
  try {
    const st = await fetchOcStatus();
    health.value = {
      ...(health.value || {}),
      opencode: st.opencode,
    };
    if (st.opencode?.ok) {
      probeMsg.value = "探测成功：OpenCode 在线。";
    } else {
      probeMsg.value = `仍离线（${st.opencode?.error || "unreachable"}）。请确认 serve 已启动且端口正确。`;
    }
  } catch (e) {
    probeMsg.value = e.message || "探测失败";
  } finally {
    probing.value = false;
  }
}

async function copyCmd(cmd) {
  try {
    await navigator.clipboard.writeText(cmd);
    probeMsg.value = "已复制到剪贴板";
  } catch {
    probeMsg.value = "复制失败，请手动选择命令";
  }
}

function goChat() {
  router.push({ name: "chat" });
}

function goSkills() {
  router.push({ name: "skills" });
}

async function onLogout() {
  try {
    await logout();
  } catch {
    /* still leave */
  }
  await router.replace({ name: "login" });
}
</script>
