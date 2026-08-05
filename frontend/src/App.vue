<template>
  <div class="app-shell">
    <header class="topbar" role="banner">
      <div class="brand-block">
        <div class="brand">财务共享中台</div>
        <span class="brand-sub">{{ pageTitle }}</span>
      </div>
      <nav v-if="showNav" class="top-nav" aria-label="主导航">
        <RouterLink
          v-for="item in visibleNav"
          :key="item.name"
          :to="{ name: item.name }"
          class="nav-link"
          :class="{ active: route.name === item.name }"
        >
          <el-icon style="vertical-align: -2px; margin-right: 4px">
            <component :is="item.icon" />
          </el-icon>
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="topbar-actions">
        <el-button
          size="small"
          plain
          class="theme-btn"
          @click="onToggleTheme"
          :title="theme === 'neon' ? '切换到浅色' : '切换到暗色'"
        >
          <el-icon><component :is="theme === 'neon' ? 'Sunny' : 'Moon'" /></el-icon>
          {{ theme === "neon" ? "暗色" : "浅色" }}
        </el-button>
        <template v-if="showNav && currentUser">
          <span class="user-chip" :title="currentUser.username">
            {{ currentUser.display_name || currentUser.username }}
            <el-tag v-if="currentUser.role === 'admin'" size="small" type="warning" effect="dark">
              管理
            </el-tag>
          </span>
          <el-button size="small" plain class="theme-btn" @click="onLogout">
            登出
          </el-button>
        </template>
      </div>
    </header>
    <main class="main" :class="{ wide: isWide }">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { fetchMe, logout } from "./api/client";
import { getStoredTheme, initTheme, toggleTheme } from "./theme";

const route = useRoute();
const router = useRouter();
const theme = ref(getStoredTheme());
const currentUser = ref(null);

const allNav = [
  { name: "home", label: "工作台", icon: "HomeFilled", adminOnly: false },
  { name: "chat", label: "智能对话", icon: "ChatDotRound", adminOnly: false },
  { name: "skills", label: "技能目录", icon: "Collection", adminOnly: false },
  { name: "admin", label: "管理", icon: "Setting", adminOnly: true },
];

const showNav = computed(() => route.name !== "login");
const isWide = computed(() => route.name !== "login");
const visibleNav = computed(() => {
  const isAdmin = currentUser.value?.role === "admin";
  return allNav.filter((item) => !item.adminOnly || isAdmin);
});

const pageTitle = computed(() => {
  const map = {
    login: "登录",
    home: "工作台",
    chat: "智能对话",
    skills: "技能目录",
    admin: "管理",
  };
  return map[route.name] || "财务共享中台";
});

onMounted(() => {
  theme.value = initTheme();
  refreshUser();
});

watch(
  () => route.name,
  () => {
    if (route.name !== "login") refreshUser();
    else currentUser.value = null;
  },
);

async function refreshUser() {
  if (route.name === "login") {
    currentUser.value = null;
    return;
  }
  try {
    const data = await fetchMe();
    currentUser.value = data.user || null;
  } catch {
    currentUser.value = null;
  }
}

function onToggleTheme() {
  theme.value = toggleTheme();
}

async function onLogout() {
  try {
    await logout();
  } catch {
    /* still leave */
  }
  currentUser.value = null;
  ElMessage.success("已登出");
  await router.replace({ name: "login" });
}
</script>

<style scoped>
.theme-btn {
  --el-button-bg-color: transparent;
  --el-button-text-color: var(--topbar-ink);
  --el-button-border-color: rgba(255, 255, 255, 0.22);
  --el-button-hover-bg-color: var(--nav-active);
  --el-button-hover-text-color: var(--accent);
  --el-button-hover-border-color: var(--accent);
}

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--topbar-ink);
  opacity: 0.92;
  max-width: 12rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
