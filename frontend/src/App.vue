<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">财务共享中台</div>
      <div class="topbar-actions">
        <span class="phase">工作台 · OC 可选</span>
        <button
          type="button"
          class="ghost"
          @click="onToggleTheme"
          :title="theme === 'neon' ? '切换到浅色' : '切换到 Neon 暗色'"
        >
          {{ theme === "neon" ? "主题: Neon" : "主题: Light" }}
        </button>
      </div>
    </header>
    <main class="main" :class="{ wide: isWide }">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterView, useRoute } from "vue-router";
import { getStoredTheme, initTheme, toggleTheme } from "./theme";

const route = useRoute();
const theme = ref(getStoredTheme());

const isWide = computed(
  () => route.name === "home" || route.name === "chat" || route.name === "skills",
);

onMounted(() => {
  theme.value = initTheme();
});

function onToggleTheme() {
  theme.value = toggleTheme();
}
</script>
