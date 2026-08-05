<template>
  <div class="page">
    <header class="page-header">
      <div class="row" style="justify-content: space-between; width: 100%">
        <div>
          <h1>管理</h1>
          <p class="lead">
            授权已上架技能、查看审计日志、同步 Skills 仓。权限以服务端为准；非管理员无法使用本页。
          </p>
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
    />

    <StateBlock v-if="loading" kind="loading" />

    <template v-else-if="isAdmin">
      <div class="grid">
        <section class="panel">
          <h2>技能授权</h2>
          <p class="muted">
            将已发布技能授予用户（填用户 ID）或角色（如 <code>user</code>）。用户 ID 可在下方说明中获取方式。
          </p>
          <el-form label-position="top" @submit.prevent="onGrant">
            <el-form-item label="已发布技能">
              <el-select
                v-model="grantSkillId"
                placeholder="选择技能"
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="s in publishedSkills"
                  :key="s.id"
                  :label="`${s.title || s.skill_key} (${s.skill_key})`"
                  :value="s.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="主体类型">
              <el-radio-group v-model="principalType">
                <el-radio value="user">用户 ID</el-radio>
                <el-radio value="role">角色名</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item :label="principalType === 'user' ? '用户 ID' : '角色'">
              <el-input
                v-model="principalId"
                :placeholder="
                  principalType === 'user'
                    ? '例如用户 UUID（暂无用户列表时可用测试账号 id）'
                    : 'user 或 admin'
                "
              />
            </el-form-item>
            <el-button type="primary" :loading="granting" native-type="submit">
              授予运行权
            </el-button>
          </el-form>
          <p class="muted" style="margin-top: 12px">
            说明：当前版本尚未提供开户列表 UI（产品边界·Phase2）。授权对象可用「角色 user」一次授给全体普通角色，或使用用户 UUID。
            <template v-if="me?.id">
              当前登录用户 ID：<code>{{ me.id }}</code>
            </template>
          </p>
        </section>

        <section class="panel">
          <h2>Skills 仓同步</h2>
          <p class="muted">从本机 <code>FSA_SKILLS_ROOT</code> 读取 catalog.yaml 写入已发布技能。</p>
          <el-button type="primary" :loading="syncing" @click="onSync">
            同步 Skills 仓
          </el-button>
          <p v-if="syncMsg" class="muted" style="margin-top: 8px">{{ syncMsg }}</p>
        </section>
      </div>

      <section class="panel" style="margin-top: 16px">
        <div class="row" style="justify-content: space-between; margin-bottom: 12px">
          <h2 style="margin: 0">审计日志（最近）</h2>
          <el-button size="small" :loading="auditLoading" @click="loadAudit">刷新</el-button>
        </div>
        <el-table
          v-if="auditItems.length"
          :data="auditItems"
          stripe
          size="small"
          style="width: 100%"
          empty-text="暂无记录"
        >
          <el-table-column prop="ts" label="时间" min-width="160" />
          <el-table-column prop="action" label="动作" min-width="120" />
          <el-table-column prop="summary" label="摘要" min-width="220" />
          <el-table-column prop="actor_user_id" label="操作者" min-width="120" show-overflow-tooltip />
        </el-table>
        <StateBlock
          v-else-if="!auditLoading"
          kind="empty"
          title="暂无审计记录"
          detail="登录、同步、授权等操作后会显示在此。"
        />
      </section>
    </template>

    <StateBlock
      v-else
      kind="error"
      title="无管理权限"
      detail="本页仅管理员可用。请使用管理员账号登录，或联系管理员开通。"
    >
      <el-button type="primary" @click="$router.push({ name: 'home' })">回工作台</el-button>
    </StateBlock>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import StateBlock from "../components/StateBlock.vue";
import {
  fetchAdminAudit,
  fetchMe,
  fetchSkills,
  putGrant,
  syncSkills,
} from "../api/client";

const router = useRouter();
const loading = ref(true);
const error = ref("");
const me = ref(null);
const publishedSkills = ref([]);
const grantSkillId = ref("");
const principalType = ref("role");
const principalId = ref("user");
const granting = ref(false);
const syncing = ref(false);
const syncMsg = ref("");
const auditItems = ref([]);
const auditLoading = ref(false);

const isAdmin = computed(() => me.value?.role === "admin");

onMounted(load);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const m = await fetchMe();
    me.value = m.user;
    if (me.value.role !== "admin") {
      return;
    }
    const sk = await fetchSkills("runnable");
    publishedSkills.value = (sk.items || []).filter(
      (s) => s.visibility === "published" || s.runnable,
    );
    if (!grantSkillId.value && publishedSkills.value.length) {
      grantSkillId.value = publishedSkills.value[0].id;
    }
    await loadAudit();
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

async function loadAudit() {
  auditLoading.value = true;
  try {
    const data = await fetchAdminAudit(40);
    auditItems.value = data.items || [];
  } catch (e) {
    error.value = e.message || "审计加载失败";
  } finally {
    auditLoading.value = false;
  }
}

async function onGrant() {
  if (!grantSkillId.value || !principalId.value.trim()) {
    ElMessage.warning("请选择技能并填写主体");
    return;
  }
  granting.value = true;
  error.value = "";
  try {
    await putGrant(grantSkillId.value, principalType.value, principalId.value.trim());
    ElMessage.success("已授予运行权");
    await loadAudit();
  } catch (e) {
    error.value = e.message || "授权失败";
  } finally {
    granting.value = false;
  }
}

async function onSync() {
  syncing.value = true;
  syncMsg.value = "";
  try {
    const r = await syncSkills(false);
    if (r.ok) {
      syncMsg.value = `同步成功：${r.upserted} 项`;
      ElMessage.success("同步成功");
      const sk = await fetchSkills("runnable");
      publishedSkills.value = sk.items || [];
      await loadAudit();
    } else {
      error.value = r.message || r.error || "同步失败";
    }
  } catch (e) {
    error.value = e.message || "同步失败";
  } finally {
    syncing.value = false;
  }
}
</script>
