<template>
  <div class="page">
    <header class="page-header">
      <h1>工作台</h1>
      <p class="lead">
        您在财务共享中台。中台可独立使用；OpenCode 为可选增强（浏览器永不直连 OC）。
      </p>
    </header>

    <StateBlock
      v-if="bootLoading"
      kind="loading"
      title="加载中"
    />
    <el-alert
      v-else-if="error"
      type="error"
      :title="error"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    >
      <template #default>
        <el-button size="small" @click="boot">重试</el-button>
      </template>
    </el-alert>

    <template v-else>
      <div class="grid">
        <section class="panel">
          <h2>
            <el-icon style="vertical-align: -2px"><User /></el-icon>
            当前用户
          </h2>
          <p class="meta-line">
            用户名：<strong>{{ user?.username || "—" }}</strong>
          </p>
          <p class="meta-line">
            角色：
            <el-tag size="small" type="info">{{ user?.role || "—" }}</el-tag>
          </p>
          <p v-if="user?.display_name" class="meta-line">
            显示名：<strong>{{ user.display_name }}</strong>
          </p>
          <div class="row" style="margin-top: 16px">
            <el-button @click="onLogout">登出</el-button>
            <el-button v-if="user?.role === 'admin'" type="primary" @click="goAdmin">
              管理
            </el-button>
          </div>
        </section>

        <section class="panel">
          <h2>
            <el-icon style="vertical-align: -2px"><DataLine /></el-icon>
            我的概况
          </h2>
          <p class="meta-line">
            已发布技能总数：
            <strong>{{ stats?.skill_total ?? "—" }}</strong>
          </p>
          <p class="meta-line">
            我可运行：
            <strong>{{ stats?.skill_runnable ?? "—" }}</strong>
          </p>
          <p class="meta-line">
            我的会话：
            <strong>{{ stats?.chat_count ?? "—" }}</strong>
          </p>
          <p class="muted" style="margin-top: 8px">
            「可运行」= 已发布且已授权给您（管理员默认可跑全部已发布）。
          </p>
        </section>

        <section class="panel">
          <h2>
            <el-icon style="vertical-align: -2px"><Monitor /></el-icon>
            系统状态
          </h2>
          <p class="meta-line">
            中台：
            <span class="chip" :class="health?.status === 'ok' ? 'ok' : 'off'">
              {{ healthLabel }}
            </span>
          </p>
          <p class="meta-line">
            数据库：
            <span class="chip" :class="health?.db?.ok ? 'ok' : 'off'">
              {{ health?.db?.ok ? "可用" : "异常" }}
            </span>
          </p>
          <p class="meta-line">
            Skills 仓：
            <span class="chip" :class="health?.skills_repo?.ok ? 'ok' : 'off'">
              {{ skillsLabel }}
            </span>
          </p>
          <p class="muted" style="margin-top: 8px">
            {{ statusHint }}
          </p>
        </section>

        <section class="panel">
          <h2>
            <el-icon style="vertical-align: -2px"><Cpu /></el-icon>
            OpenCode（可选）
          </h2>
          <p class="meta-line">
            状态：
            <span class="chip" :class="ocOnline ? 'ok' : 'off'">
              {{ ocOnline ? "在线" : "离线" }}
            </span>
          </p>
          <p class="meta-line">
            地址：<strong>{{ health?.opencode?.endpoint || "—" }}</strong>
          </p>
          <p class="meta-line">
            版本：<strong>{{ health?.opencode?.version || "未知" }}</strong>
          </p>
          <p v-if="!ocOnline" class="muted">
            离线时仍可登录、浏览技能与会话历史；发送消息前请启用 OpenCode。
          </p>
          <div class="row" style="margin-top: 12px">
            <el-button v-if="!ocOnline" type="primary" @click="openOcGuide">
              启用 OpenCode
            </el-button>
            <el-button @click="refreshHealth">重新探测</el-button>
          </div>
          <p v-if="probeMsg" class="muted" style="margin-top: 8px">{{ probeMsg }}</p>
        </section>
      </div>

      <h2 class="section-title">您可以做什么</h2>
      <div class="grid">
        <button class="entry-card" type="button" @click="goChat">
          <div class="entry-icon"><el-icon><ChatDotRound /></el-icon></div>
          <h3>智能对话</h3>
          <p class="hint">与助手协作处理单据与核对；发送消息需要 OpenCode 在线。</p>
        </button>
        <button class="entry-card" type="button" @click="goSkills">
          <div class="entry-icon"><el-icon><Collection /></el-icon></div>
          <h3>技能目录</h3>
          <p class="hint">查看已发布且授权给您的技能；无需 OpenCode 即可浏览。</p>
        </button>
        <button class="entry-card" type="button" @click="showCaps = !showCaps">
          <div class="entry-icon"><el-icon><InfoFilled /></el-icon></div>
          <h3>能力说明</h3>
          <p class="hint">哪些功能不依赖 OpenCode、哪些需要——诚实说明。</p>
        </button>
        <button
          v-if="user?.role === 'admin'"
          class="entry-card"
          type="button"
          @click="goAdmin"
        >
          <div class="entry-icon"><el-icon><Setting /></el-icon></div>
          <h3>管理</h3>
          <p class="hint">授权技能、查看审计日志、同步 Skills 仓。</p>
        </button>
      </div>

      <section class="panel" style="margin-top: 16px">
        <div class="row" style="justify-content: space-between">
          <h2 style="margin: 0">最近会话</h2>
          <el-button link type="primary" @click="goChat">全部对话</el-button>
        </div>
        <ul v-if="recentChats.length" class="honest-list" style="margin-top: 12px">
          <li v-for="c in recentChats" :key="c.id">
            <a href="#" @click.prevent="openChat(c.id)">{{ c.title || "会话" }}</a>
            <span class="muted" v-if="!c.oc_bound"> · 未绑定 OC</span>
          </li>
        </ul>
        <p v-else class="muted" style="margin-top: 12px">
          暂无会话。可到「智能对话」新建；OpenCode 离线时也可先建会话。
        </p>
      </section>

      <section v-if="showCaps" class="panel" style="margin-top: 16px">
        <h2>能力边界</h2>
        <ul class="honest-list">
          <li>
            <strong>不依赖 OpenCode</strong>：登录、工作台、健康状态、主题、技能目录、会话列表与历史
          </li>
          <li>
            <strong>依赖 OpenCode</strong>：发送对话、模型列表与推理（密钥只在 OC 侧）
          </li>
          <li>中台不会静默安装软件；启用 OC 需您确认后在本机执行命令</li>
        </ul>
      </section>
    </template>

    <el-dialog
      v-model="showGuide"
      :title="guide?.title || '启用 OpenCode'"
      width="560px"
      destroy-on-close
    >
      <p class="muted">{{ guide?.summary }}</p>
      <template v-if="!confirmed">
        <el-alert
          type="warning"
          :title="guide?.confirm_text || '请确认后再查看本机命令'"
          show-icon
          :closable="false"
          style="margin: 12px 0"
        />
        <div class="row">
          <el-button type="primary" @click="confirmed = true">我确认，查看命令</el-button>
          <el-button @click="showGuide = false">取消</el-button>
        </div>
      </template>
      <template v-else>
        <div v-for="(c, i) in guide?.commands || []" :key="i" style="margin-bottom: 12px">
          <p class="meta-line"><strong>{{ c.label }}</strong></p>
          <pre class="cmd-block">{{ c.cmd }}</pre>
          <el-button size="small" @click="copyCmd(c.cmd)">复制命令</el-button>
        </div>
        <p class="muted">{{ guide?.after_start }}</p>
        <ul class="honest-list">
          <li v-for="(t, i) in guide?.troubleshooting || []" :key="i">{{ t }}</li>
        </ul>
        <div class="row" style="margin-top: 16px">
          <el-button type="primary" :loading="probing" @click="onIStarted">
            我已启动
          </el-button>
          <el-button @click="showGuide = false">关闭</el-button>
        </div>
        <p v-if="probeMsg" class="muted" style="margin-top: 8px">{{ probeMsg }}</p>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import {
  ChatDotRound,
  Collection,
  Cpu,
  DataLine,
  InfoFilled,
  Monitor,
  Setting,
  User,
} from "@element-plus/icons-vue";
import StateBlock from "../components/StateBlock.vue";
import {
  fetchDashboardStats,
  fetchHealth,
  fetchMe,
  fetchOcEnableGuide,
  fetchOcStatus,
  listChats,
  logout,
} from "../api/client";

const router = useRouter();
const route = useRoute();
const user = ref(null);
const health = ref(null);
const stats = ref(null);
const recentChats = ref([]);
const error = ref("");
const bootLoading = ref(true);
const showCaps = ref(false);
const showGuide = ref(false);
const confirmed = ref(false);
const guide = ref(null);
const probing = ref(false);
const probeMsg = ref("");

const ocOnline = computed(() => Boolean(health.value?.opencode?.ok));
const healthLabel = computed(() => {
  if (!health.value) return "检测中";
  return health.value.status === "ok" ? "正常" : "降级/异常";
});
const skillsLabel = computed(() => {
  const s = health.value?.skills_repo;
  if (!s) return "未知";
  if (s.ok) return "已就绪";
  return s.error === "skills_root_missing" ? "未配置本地仓" : "不可用";
});
const statusHint = computed(() => {
  if (health.value?.status === "ok" && health.value?.db?.ok) {
    return "系统可正常使用。若需 AI 对话，请确保 OpenCode 在线。";
  }
  return "系统状态异常，请联系管理员或检查本机数据库配置。";
});

onMounted(boot);

async function boot() {
  bootLoading.value = true;
  error.value = "";
  try {
    const me = await fetchMe();
    user.value = me.user;
    await Promise.all([refreshHealth(), loadStats(), loadRecentChats()]);
    if (route.query.oc === "1") await openOcGuide();
  } catch {
    await router.replace({ name: "login" });
  } finally {
    bootLoading.value = false;
  }
}

async function loadStats() {
  try {
    stats.value = await fetchDashboardStats();
  } catch {
    stats.value = null;
  }
}

async function loadRecentChats() {
  try {
    const data = await listChats();
    recentChats.value = (data.items || []).slice(0, 5);
  } catch {
    recentChats.value = [];
  }
}

async function refreshHealth() {
  try {
    health.value = await fetchHealth();
    probeMsg.value = "";
  } catch (e) {
    error.value = e.message || "无法加载系统状态，请检查中台服务是否启动";
  }
}

async function openOcGuide() {
  confirmed.value = false;
  probeMsg.value = "";
  try {
    guide.value = await fetchOcEnableGuide();
    showGuide.value = true;
  } catch (e) {
    ElMessage.error(e.message || "无法加载 OpenCode 引导");
  }
}

async function onIStarted() {
  probing.value = true;
  probeMsg.value = "";
  try {
    const st = await fetchOcStatus();
    health.value = { ...(health.value || {}), opencode: st.opencode };
    if (st.opencode?.ok) {
      probeMsg.value = "探测成功：OpenCode 在线。";
      ElMessage.success("OpenCode 在线");
    } else {
      probeMsg.value = `仍离线（${st.opencode?.error || "无法连接"}）。请确认 serve 已启动且端口正确。`;
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
    ElMessage.success("已复制到剪贴板");
  } catch {
    ElMessage.warning("复制失败，请手动选择命令");
  }
}

function goChat() {
  router.push({ name: "chat" });
}
function goSkills() {
  router.push({ name: "skills" });
}
function goAdmin() {
  router.push({ name: "admin" });
}
function openChat(id) {
  router.push({ name: "chat", query: id ? { id } : {} });
}

async function onLogout() {
  try {
    await logout();
  } catch {
    /* still leave */
  }
  ElMessage.success("已登出");
  await router.replace({ name: "login" });
}
</script>

<style scoped>
.section-title {
  margin: 28px 0 12px;
  font-size: 18px;
  font-weight: 650;
}
</style>
