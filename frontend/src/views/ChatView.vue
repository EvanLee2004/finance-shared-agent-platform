<template>
  <div class="chat-layout">
    <aside class="chat-sidebar">
      <div class="row" style="margin-bottom: 0.75rem">
        <button class="secondary" type="button" @click="goHome">工作台</button>
        <button type="button" :disabled="creating" @click="onCreate">
          {{ creating ? "…" : "新建" }}
        </button>
      </div>
      <p v-if="listError" class="error">{{ listError }}</p>
      <button
        v-for="c in chats"
        :key="c.id"
        type="button"
        class="chat-list-item"
        :class="{ active: c.id === activeId }"
        @click="selectChat(c.id)"
      >
        {{ c.title || "会话" }}
        <span v-if="!c.oc_bound" style="opacity: 0.6; font-size: 0.75rem">
          · 未绑定 OC
        </span>
      </button>
      <p v-if="!chats.length && !listError" class="sub">暂无会话，点「新建」。</p>
    </aside>

    <section class="chat-main">
      <div class="model-bar">
        <label for="model-select">模型（来自 OpenCode）</label>
        <div class="row">
          <select
            id="model-select"
            v-model="selectedKey"
            :disabled="!ocModelsOk || !models.length || sending"
            @change="onModelChange"
          >
            <option v-if="!models.length" value="" disabled>
              {{ modelPlaceholder }}
            </option>
            <option v-for="m in models" :key="m.key" :value="m.key">
              {{ formatModelLabel(m) }}
            </option>
          </select>
          <button
            class="secondary"
            type="button"
            :disabled="modelsLoading"
            @click="loadModels"
          >
            {{ modelsLoading ? "…" : "刷新列表" }}
          </button>
        </div>
        <p class="model-hint">
          <template v-if="!ocModelsOk">
            OpenCode 离线或不可用 — 请先启用 OC。中台不维护模型白名单。
          </template>
          <template v-else-if="!models.length">
            无可用模型，请在 OpenCode 配置 provider（/connect 或 opencode.json）。
          </template>
          <template v-else>
            当前：
            <strong>{{ selectedKey || "—" }}</strong>
            · 共 {{ models.length }} 个（OC 返回）
          </template>
        </p>
      </div>

      <div class="messages" ref="msgBox">
        <p v-if="!activeId" class="bubble system">
          选择或新建会话。模型列表完全来自本机 OpenCode；发送时携带所选
          providerID/modelID。
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
      </div>
      <div class="composer">
        <p v-if="sendError" class="error" role="alert">{{ sendError }}</p>
        <textarea
          v-model="draft"
          placeholder="输入消息…（同步等待 OC 回复）"
          :disabled="!activeId || sending"
          @keydown.meta.enter="onSend"
          @keydown.ctrl.enter="onSend"
        />
        <div class="row">
          <button
            type="button"
            :disabled="!activeId || sending || !draft.trim()"
            @click="onSend"
          >
            {{ sending ? "发送中…" : "发送" }}
          </button>
          <button class="secondary" type="button" @click="goEnableOc">
            启用 OpenCode
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
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
const sendError = ref("");
const creating = ref(false);
const sending = ref(false);
const msgBox = ref(null);

const models = ref([]);
const ocModelsOk = ref(false);
const modelsLoading = ref(false);
const selectedKey = ref("");
const modelsError = ref("");

const modelPlaceholder = computed(() => {
  if (modelsLoading.value) return "加载中…";
  if (!ocModelsOk.value) return "先启用 OpenCode";
  return "无可用模型";
});

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
  modelsError.value = "";
  try {
    const data = await fetchOcModels();
    ocModelsOk.value = Boolean(data.ok);
    models.value = Array.isArray(data.items) ? data.items : [];
    // restore last choice if still in list; else first item
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
    if (!data.ok) {
      modelsError.value = data.error || "oc offline";
    }
  } catch (e) {
    if (e.status === 401) {
      await router.replace({ name: "login" });
      return;
    }
    ocModelsOk.value = false;
    models.value = [];
    modelsError.value = e.message || "加载失败";
  } finally {
    modelsLoading.value = false;
  }
}

async function reloadChats() {
  listError.value = "";
  try {
    const data = await listChats();
    chats.value = data.items || [];
  } catch (e) {
    if (e.status === 401) {
      await router.replace({ name: "login" });
      return;
    }
    listError.value = e.message || "加载失败";
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
    if (data.chat?.id) await selectChat(data.chat.id);
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
  const text = draft.value.trim();
  const model = selectedModel();
  try {
    const data = await sendMessage(activeId.value, text, model);
    draft.value = "";
    if (data.user_message) messages.value.push(data.user_message);
    if (data.assistant_message) messages.value.push(data.assistant_message);
    if (data.model) {
      // keep UI in sync with what was sent
      const k = `${data.model.providerID}/${data.model.modelID}`;
      if (k) selectedKey.value = k;
    }
    await scrollBottom();
    await reloadChats();
  } catch (e) {
    if (e.code === "oc_unavailable") {
      sendError.value =
        e.message ||
        "OpenCode 未就绪。请点「启用 OpenCode」或回工作台完成引导后再发送。";
    } else {
      sendError.value = e.message || "发送失败";
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
