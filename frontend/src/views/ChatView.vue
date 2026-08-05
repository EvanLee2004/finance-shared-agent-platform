<template>
  <div class="page">
    <header class="page-header">
      <h1>智能对话</h1>
      <p class="lead">
        与助手协作。模型列表来自本机 OpenCode，中台不维护白名单；离线时可建会话、看历史，发送需 OC 在线。
      </p>
    </header>

    <div class="chat-layout">
      <aside class="chat-sidebar">
        <div class="row">
          <el-button @click="goHome">工作台</el-button>
          <el-button type="primary" :loading="creating" @click="onCreate">
            新建会话
          </el-button>
        </div>
        <div v-if="listError" style="margin-bottom: 8px">
          <el-alert
            type="error"
            :title="listError"
            show-icon
            :closable="false"
          />
          <el-button
            size="small"
            style="margin-top: 8px"
            :loading="listLoading"
            @click="reloadChats"
          >
            重试
          </el-button>
        </div>
        <StateBlock v-if="listLoading" kind="loading" :rows="3" />
        <template v-else-if="chats.length">
          <button
            v-for="c in chats"
            :key="c.id"
            type="button"
            class="chat-list-item"
            :class="{ active: c.id === activeId }"
            @click="selectChat(c.id)"
          >
            {{ c.title || "会话" }}
            <span v-if="!c.oc_bound" class="muted" style="font-size: 12px">
              · 未绑定 OC
            </span>
          </button>
        </template>
        <StateBlock
          v-else-if="!listError"
          kind="empty"
          title="还没有会话"
          detail="点击「新建会话」开始。即使 OpenCode 离线也可以先建好会话。"
        />
      </aside>

      <section class="chat-main">
        <div class="model-bar">
          <div class="row" style="width: 100%">
            <span class="muted" style="min-width: 4.5rem">模型</span>
            <el-select
              v-model="selectedKey"
              placeholder="选择模型"
              :disabled="!ocModelsOk || !models.length || sending"
              filterable
              style="flex: 1; min-width: 160px"
              @change="onModelChange"
            >
              <el-option
                v-for="m in models"
                :key="m.key"
                :label="formatModelLabel(m)"
                :value="m.key"
              />
            </el-select>
            <el-button :loading="modelsLoading" @click="loadModels">刷新</el-button>
          </div>
          <p class="model-hint">
            <template v-if="!ocModelsOk">
              OpenCode 离线 — 请到工作台「启用 OpenCode」。中台不维护模型名单。
            </template>
            <template v-else-if="!models.length">
              暂无可用模型。请在 OpenCode 配置 provider 后点「刷新」。
            </template>
            <template v-else>
              当前 <strong>{{ selectedKey || "—" }}</strong>
              · 共 {{ models.length }} 个（OpenCode 返回）
            </template>
          </p>
        </div>

        <div class="messages" ref="msgBox">
          <p v-if="!activeId" class="bubble system">
            请在左侧选择或新建会话。发送时会带上所选模型的 provider / model 标识。
          </p>
          <div
            v-for="m in messages"
            :key="m.id"
            class="bubble"
            :class="m.role"
          >
            <strong v-if="m.role === 'user'">我</strong>
            <strong v-else-if="m.role === 'assistant'">助手</strong>
            <div>{{ m.content_text }}</div>
          </div>
          <el-skeleton v-if="sending" :rows="2" animated style="max-width: 70%" />
        </div>

        <div class="composer">
          <div v-if="sendError" style="margin-bottom: 12px" role="alert">
            <el-alert
              type="error"
              :title="sendError"
              show-icon
              :closable="false"
            />
            <div class="row" style="margin-top: 8px">
              <el-button
                size="small"
                type="primary"
                :loading="sending"
                :disabled="!activeId || !draft.trim()"
                @click="onSend"
              >
                重试发送
              </el-button>
              <el-button
                v-if="sendErrorIsOc"
                size="small"
                @click="goEnableOc"
              >
                去启用 OpenCode
              </el-button>
            </div>
          </div>
          <el-input
            v-model="draft"
            type="textarea"
            :rows="3"
            placeholder="输入消息…（Ctrl/⌘ + Enter 发送）"
            :disabled="!activeId || sending"
            @keydown.meta.enter.prevent="onSend"
            @keydown.ctrl.enter.prevent="onSend"
          />
          <div class="row" style="margin-top: 12px">
            <el-button
              type="primary"
              :loading="sending"
              :disabled="!activeId || !draft.trim()"
              @click="onSend"
            >
              发送
            </el-button>
            <el-button @click="goEnableOc">启用 OpenCode</el-button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import StateBlock from "../components/StateBlock.vue";
import {
  createChat,
  fetchOcModels,
  listChats,
  listMessages,
  sendMessage,
} from "../api/client";

const LS_MODEL = "fsa_selected_model_key";
const router = useRouter();
const chats = ref([]);
const activeId = ref(null);
const messages = ref([]);
const draft = ref("");
const listError = ref("");
const listLoading = ref(true);
const sendError = ref("");
const sendErrorIsOc = ref(false);
const creating = ref(false);
const sending = ref(false);
const msgBox = ref(null);
const models = ref([]);
const ocModelsOk = ref(false);
const modelsLoading = ref(false);
const selectedKey = ref("");

onMounted(async () => {
  await Promise.all([reloadChats(), loadModels()]);
});

function formatModelLabel(m) {
  const free = m.free === true ? " · free" : "";
  return `${m.name || m.modelID} (${m.providerID})${free}`;
}

function onModelChange() {
  try {
    if (selectedKey.value) localStorage.setItem(LS_MODEL, selectedKey.value);
  } catch {
    /* ignore */
  }
}

function selectedModel() {
  const m = models.value.find((x) => x.key === selectedKey.value);
  if (!m) return null;
  return { providerID: m.providerID, modelID: m.modelID };
}

async function loadModels() {
  modelsLoading.value = true;
  try {
    const data = await fetchOcModels();
    ocModelsOk.value = Boolean(data.ok);
    models.value = Array.isArray(data.items) ? data.items : [];
    let last = "";
    try {
      last = localStorage.getItem(LS_MODEL) || "";
    } catch {
      last = "";
    }
    if (last && models.value.some((m) => m.key === last)) {
      selectedKey.value = last;
    } else if (models.value.length) {
      selectedKey.value = models.value[0].key;
      onModelChange();
    } else {
      selectedKey.value = "";
    }
  } catch (e) {
    if (e.status === 401) {
      await router.replace({ name: "login" });
      return;
    }
    ocModelsOk.value = false;
    models.value = [];
  } finally {
    modelsLoading.value = false;
  }
}

async function reloadChats() {
  listLoading.value = true;
  listError.value = "";
  try {
    const data = await listChats();
    chats.value = data.items || [];
  } catch (e) {
    if (e.status === 401) {
      await router.replace({ name: "login" });
      return;
    }
    listError.value = e.message || "无法加载会话列表，请检查网络或重新登录";
  } finally {
    listLoading.value = false;
  }
}

async function selectChat(id) {
  activeId.value = id;
  sendError.value = "";
  try {
    const data = await listMessages(id);
    messages.value = data.items || [];
    await scrollBottom();
  } catch (e) {
    sendError.value = e.message || "无法加载消息";
    messages.value = [];
  }
}

async function onCreate() {
  creating.value = true;
  sendError.value = "";
  try {
    const data = await createChat("新对话");
    await reloadChats();
    if (data.chat?.id) {
      await selectChat(data.chat.id);
      ElMessage.success("已新建会话");
    }
  } catch (e) {
    sendError.value = e.message || "创建失败";
  } finally {
    creating.value = false;
  }
}

async function onSend() {
  if (!activeId.value || !draft.value.trim() || sending.value) return;
  sending.value = true;
  sendError.value = "";
  sendErrorIsOc.value = false;
  const text = draft.value.trim();
  const model = selectedModel();
  try {
    const data = await sendMessage(activeId.value, text, model);
    draft.value = "";
    if (data.user_message) messages.value.push(data.user_message);
    if (data.assistant_message) messages.value.push(data.assistant_message);
    if (data.model) {
      const k = `${data.model.providerID}/${data.model.modelID}`;
      if (k) selectedKey.value = k;
    }
    await scrollBottom();
    await reloadChats();
  } catch (e) {
    if (e.code === "oc_unavailable") {
      sendErrorIsOc.value = true;
      sendError.value =
        e.message ||
        "OpenCode 未就绪。请点「启用 OpenCode」或回工作台完成引导后再发送。";
    } else {
      sendError.value = e.message || "发送失败，请稍后重试";
    }
  } finally {
    sending.value = false;
  }
}

async function scrollBottom() {
  await nextTick();
  if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight;
}

function goHome() {
  router.push({ name: "home" });
}
function goEnableOc() {
  router.push({ name: "home", query: { oc: "1" } });
}
</script>
