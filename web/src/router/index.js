import { createRouter, createWebHashHistory } from 'vue-router'

// 用 hash 模式：静态托管（GitHub Pages / 任意 CDN）不需要服务端重写规则，
// 深链形如 /#/shop/B0FFG123，直接可分享。
const routes = [
  { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
  { path: '/explore/:district', name: 'explore', component: () => import('../views/ExploreView.vue'), props: true },
  { path: '/anchors', name: 'anchors', component: () => import('../views/AnchorsView.vue') },
  // 详情页把片区 slug 放进 URL：这样只需加载该片区一个文件，
  // 不必为了查一个 id 而拉取整份跨片区索引。
  { path: '/shop/:slug/:id', name: 'shop', component: () => import('../views/ShopDetailView.vue'), props: true },
  { path: '/itinerary', name: 'itinerary', component: () => import('../views/ItineraryView.vue') },
  { path: '/about', name: 'about', component: () => import('../views/AboutView.vue') },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
