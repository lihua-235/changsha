import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  // base: './' 让打包产物可以直接放到 GitHub Pages 的子路径下，
  // 配合路由使用 hash 模式（见 src/router/index.js），部署零配置。
  base: './',
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: false,
  },
  build: {
    outDir: 'dist',
    // 数据 JSON 走 public/ 原样拷贝，不参与打包
    assetsInlineLimit: 4096,
  },
})
