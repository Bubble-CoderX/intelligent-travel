import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'chat',
    component: () => import('@/components/chat/ChatContainer.vue'),
  },
  {
    path: '/trips',
    name: 'trips',
    component: () => import('@/views/TripHistory.vue'),
  },
  {
    path: '/trip-detail/:id',
    name: 'trip-detail',
    component: () => import('@/views/TripDetail.vue'),
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/ProfilePage.vue'),
  },
  {
    path: '/knowledge',
    name: 'knowledge',
    component: () => import('@/views/KnowledgeBrowser.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
