<template>
  <div class="workbench">
    <div class="row" style="margin-bottom: 1rem">
      <button class="secondary" type="button" @click="$router.push({ name: 'home' })">
        工作台
      </button>
      <button
        v-if="isAdmin"
        type="button"
        :disabled="syncing"
        @click="onSync"
      >
        {{ syncing ? "同步中…" : "同步 Skills 仓" }}
      </button>
    </div>
    <h1>技能目录</h1>
    <p class="sub">
      {{ note || "published ∩ 授权可运行；管理员默认可跑全部已发布技能。中台无 OC 也可浏览本目录。" }}
    </p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="syncMsg" class="ok-msg">{{ syncMsg }}</p>

    <div v-if="loading" class="panel empty-state">
      <p class="sub">正在加载技能列表…</p>
    </div>
    <div v-else-if="!items.length" class="panel empty-state">
      <h2>暂无可用技能</h2>
      <p class="sub">
        管理员可配置本机
        <code>FSA_SKILLS_ROOT</code>
        指向 finance-shared-skills，并点击「同步 Skills 仓」。
        普通用户需被授予 published 技能后方可运行。
      </p>
    </div>
    <div v-else class="grid">
      <section v-for="s in items" :key="s.skill_key || s.id" class="panel">
        <h2>{{ s.title || s.skill_key }}</h2>
        <p>{{ s.summary }}</p>
        <p class="meta-line">
          版本：<strong>{{ s.current_version || "—" }}</strong>
        </p>
        <p class="meta-line">
          可运行：
          <span class="chip" :class="s.runnable !== false ? 'ok' : 'off'">
            {{ s.runnable === false ? "否" : "是" }}
          </span>
        </p>
        <p v-if="s.requires_opencode != null" class="meta-line">
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
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { fetchMe, fetchSkills, fetchSkillsCatalog, syncSkills } from "../api/client";

const router = useRouter();
const items = ref([]);
const note = ref("");
const error = ref("");
const syncMsg = ref("");
const loading = ref(true);
const syncing = ref(false);
const me = ref(null);

const isAdmin = computed(() => me.value?.role === "admin");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const meData = await fetchMe();
    me.value = meData.user;
    // Prefer /skills runnable; fall back to catalog compat
    try {
      const data = await fetchSkills("runnable");
      if (data.items && data.items.length) {
        items.value = data.items;
        note.value = "scope=runnable · published∩授权（admin 见全部 published）";
        return;
      }
    } catch {
      /* fall through */
    }
    const cat = await fetchSkillsCatalog();
    items.value = cat.items || [];
    note.value = cat.note || "";
  } catch (e) {
    if (e.status === 401) {
      await router.replace({ name: "login" });
      return;
    }
    error.value = e.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

async function onSync() {
  syncing.value = true;
  syncMsg.value = "";
  error.value = "";
  try {
    const r = await syncSkills(false);
    if (r.ok) {
      syncMsg.value = `同步成功：写入 ${r.upserted} 项（root=${r.root || "—"}）`;
      await load();
    } else {
      error.value = r.message || r.error || "同步失败";
    }
  } catch (e) {
    error.value = e.message || "同步失败";
  } finally {
    syncing.value = false;
  }
}

onMounted(load);
</script>
