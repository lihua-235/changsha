<script setup>
defineProps({
  title: { type: String, default: '这里还什么都没有' },
  desc: { type: String, default: '' },
  icon: { type: String, default: '○' },
})
</script>

<template>
  <div class="empty">
    <div class="empty-icon" aria-hidden="true">{{ icon }}</div>
    <h3>{{ title }}</h3>
    <p v-if="desc" class="text-muted text-sm">{{ desc }}</p>
    <div class="empty-actions">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.empty {
  text-align: center;
  padding: 44px 20px;
  border: 1px dashed var(--line);
  border-radius: var(--r);
  background: var(--bg-soft);
}
.empty-icon {
  font-size: 30px;
  color: var(--muted);
  line-height: 1;
  margin-bottom: 10px;
}
.empty h3 {
  margin-bottom: 6px;
  color: var(--ink-2);
}
.empty p {
  max-width: 32em;
  margin: 0 auto 0.9em;
}
.empty-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}
</style>
