<script setup>
import AppFooter from './components/AppFooter.vue'
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="container topbar-inner">
        <RouterLink to="/" class="brand">
          <span class="brand-mark">长沙</span> · 本地口味地图
        </RouterLink>
        <nav class="topnav">
          <RouterLink to="/">首页</RouterLink>
          <RouterLink to="/anchors">景点</RouterLink>
          <RouterLink to="/itinerary">行程</RouterLink>
          <RouterLink to="/about">关于</RouterLink>
        </nav>
      </div>
    </header>

    <main class="main">
      <div class="container">
        <RouterView />
      </div>
    </main>

    <AppFooter />
  </div>
</template>
