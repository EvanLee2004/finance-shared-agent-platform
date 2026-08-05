<template>
  <div class="app-shell">
    <header class="topbar" role="banner">
      <div class="brand-block">
        <div class="brand">财务共享中台</div>
        <span class="brand-sub">{{ pageTitle }}</span>
      </div>
      <nav v-if="showNav" class="top-nav" aria-label="主导航">
        <RouterLink
          v-for="item in navItems"
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
          :title="theme === 'neon' ? '切换到浅色' : '切换到 Neon 暗色'"
        >
          <el-icon><component :is="theme === 'neon' ? 'Sunny' : 'Moon'" /></el-icon>
          {{ theme === "neon" ? "Neon" : "Light" }}
        </el-button>
      </div>
    </header>
    <main class="main" :class="{ wide: isWide }">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";
import { getStoredTheme, initTheme, toggleTheme } from "./theme";

const route = useRoute();
const theme = ref(getStoredTheme());

const navItems = [
  { name: "home", label: "工作台", icon: "HomeFilled" },
  { name: "chat", label: "智能对话", icon: "ChatDotRound" },
  { name: "skills", label: "技能目录", icon: "Collection" },
];

const showNav = computed(() => route.name !== "login");
const isWide = computed(() => route.name !== "login");

const pageTitle = computed(() => {
  const map = {
    login: "登录",
    home: "工作台",
    chat: "智能对话",
    skills: "技能目录",
  };
  return map[route.name] || "财务共享中台";
});

onMounted(() => {
  theme.value = initTheme();
});

function onToggleTheme() {
  theme.value = toggleTheme();
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
</style>
