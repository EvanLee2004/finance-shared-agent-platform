<template>
  <div class="page">
    <header class="page-header">
      <div class="row" style="justify-content: space-between; width: 100%">
        <div>
          <h1>技能目录</h1>
          <p class="lead">
            {{ note || "仅展示已发布且授权给您的技能。管理员默认可查看全部已发布技能。" }}
          </p>
        </div>
        <div class="row">
          <el-button
            v-if="isAdmin"
            type="primary"
            :loading="syncing"
            @click="onSync"
          >
            同步 Skills 仓
          </el-button>
        </div>
      </div>
    </header>

    <el-alert
      v-if="error"
      type="error"
      :title="error"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    >
      <el-button size="small" @click="load">重试</el-button>
    </el-alert>
    <el-alert
      v-if="syncMsg"
      type="success"
      :title="syncMsg"
      show-icon
      :closable="true"
      @close="syncMsg = ''"
      style="margin-bottom: 16px"
    />

    <StateBlock v-if="loading" kind="loading" />

    <StateBlock
      v-else-if="!items.length"
      kind="empty"
      title="暂时没有可用技能"
      :detail="emptyDetail"
    >
      <el-button v-if="isAdmin" type="primary" :loading="syncing" @click="onSync">
        同步 Skills 仓
      </el-button>
    </StateBlock>

    <div v-else class="grid">
      <section v-for="s in items" :key="s.skill_key || s.id" class="panel">
        <h2>{{ s.title || s.skill_key }}</h2>
        <p class="muted">{{ s.summary }}</p>
        <p class="meta-line">
          版本：<strong>{{ s.current_version || "—" }}</strong>
        </p>
        <p class="meta-line">
          可运行：
          <el-tag
            size="small"
            :type="s.runnable === false ? 'warning' : 'success'"
          >
            {{ s.runnable === false ? "否（未授权）" : "是" }}
          </el-tag>
        </p>
        <p v-if="s.requires_opencode != null" class="meta-line">
          OpenCode：
          <el-tag size="small" :type="s.requires_opencode ? 'warning' : 'info'">
            {{ s.requires_opencode ? "运行时需要" : "浏览不需要" }}
          </el-tag>
        </p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import StateBlock from "../components/StateBlock.vue";
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
const emptyDetail = computed(() => {
  if (isAdmin.value) {
    return "请配置本机 FSA_SKILLS_ROOT 指向 finance-shared-skills 后，点击「同步 Skills 仓」。同步成功后，已发布技能会出现在此列表。";
  }
  return "您当前没有被授予可运行的已发布技能。请联系管理员在后台为您授权；浏览本页不需要 OpenCode。";
});

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const meData = await fetchMe();
    me.value = meData.user;
    try {
      const data = await fetchSkills("runnable");
      if (data.items && data.items.length) {
        items.value = data.items;
        note.value =
          "仅显示可运行技能（已发布且已授权）。管理员可看到全部已发布技能。";
        return;
      }
      items.value = [];
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
    error.value = e.message || "加载技能失败，请稍后重试";
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
      syncMsg.value = `同步成功：写入 ${r.upserted} 项`;
      ElMessage.success("技能同步成功");
      await load();
    } else {
      error.value =
        r.message ||
        r.error ||
        "同步失败。请确认本机已设置 FSA_SKILLS_ROOT 且含 catalog.yaml";
    }
  } catch (e) {
    error.value = e.message || "同步失败";
  } finally {
    syncing.value = false;
  }
}

onMounted(load);
</script>
