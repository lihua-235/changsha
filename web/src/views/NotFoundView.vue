<script setup>
import EmptyState from '../components/EmptyState.vue'
</script>

<template>
  <EmptyState icon="404" title="这个页面不存在" desc="链接可能写错了，或者这个页面还没做。">
    <RouterLink to="/" class="btn btn-primary">回首页</RouterLink>
  </EmptyState>
</template>
