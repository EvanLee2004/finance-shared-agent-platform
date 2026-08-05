<template>
  <div class="workbench">
    <div class="row" style="margin-bottom: 1rem">
      <button class="secondary" type="button" @click="$router.push({ name: 'home' })">
        工作台
      </button>
    </div>
    <h1>技能目录（只读）</h1>
    <p class="sub">{{ note }}</p>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="grid">
      <section v-for="s in items" :key="s.skill_key" class="panel">
        <h2>{{ s.title }}</h2>
        <p>{{ s.summary }}</p>
        <p class="meta-line">
          OpenCode：
          <span class="chip" :class="s.requires_opencode ? 'off' : 'ok'">
            {{ s.requires_opencode ? "需要" : "不需要" }}
          </span>
        </p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { fetchSkillsCatalog } from "../api/client";

const router = useRouter();
const items = ref([]);
const note = ref("");
const error = ref("");

onMounted(async () => {
  try {
    const data = await fetchSkillsCatalog();
    items.value = data.items || [];
    note.value = data.note || "";
  } catch (e) {
    if (e.status === 401) {
      await router.replace({ name: "login" });
      return;
    }
    error.value = e.message || "加载失败";
  }
});
</script>
