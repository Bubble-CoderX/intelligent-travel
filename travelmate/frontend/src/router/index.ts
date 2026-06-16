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
  {
    path: '/chat-history',
    name: 'chat-history',
    component: () => import('@/views/ChatHistory.vue'),
  },
  {
    path: '/weather-records',
    name: 'weather-records',
    component: () => import('@/views/WeatherRecord.vue'),
  },
  {
    path: '/travel-stats',
    name: 'travel-stats',
    component: () => import('@/views/TravelStats.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
