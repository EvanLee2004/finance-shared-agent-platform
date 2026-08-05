<template>
  <div class="state-block panel" :class="kind" role="status">
    <el-skeleton v-if="kind === 'loading'" :rows="rows" animated />
    <el-empty
      v-else-if="kind === 'empty'"
      :description="title || '暂无内容'"
      :image-size="88"
    >
      <p v-if="detail" class="muted">{{ detail }}</p>
      <slot />
    </el-empty>
    <div v-else-if="kind === 'error'" class="error-box">
      <el-alert
        type="error"
        :title="title || '出了点问题'"
        :description="detail || message"
        show-icon
        :closable="false"
      />
      <div v-if="$slots.default" class="row" style="margin-top: 12px">
        <slot />
      </div>
    </div>
    <div v-else-if="kind === 'success'">
      <el-alert type="success" :title="title || '完成'" :description="detail" show-icon :closable="false" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  kind: {
    type: String,
    default: "empty",
    validator: (v) => ["loading", "empty", "error", "success"].includes(v),
  },
  title: { type: String, default: "" },
  detail: { type: String, default: "" },
  message: { type: String, default: "" },
  rows: { type: Number, default: 4 },
});
</script>
