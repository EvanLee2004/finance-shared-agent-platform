<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">财务共享中台</div>
      <div class="phase">Phase0 · 登录地基</div>
    </header>
    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { RouterView } from "vue-router";
</script>
