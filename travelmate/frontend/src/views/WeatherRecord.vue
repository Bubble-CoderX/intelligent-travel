<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'

const props = defineProps<{ dark?: boolean; toggleDark?: () => void }>()
const router = useRouter()

interface WeatherRecord {
  id: number
  city: string
  weather: string
  temperature: number
  humidity: string
  wind_direction: string
  wind_power: string
  fetched_at: string
}

interface CityStat {
  city: string
  count: number
  latest: string
}

const records = ref<WeatherRecord[]>([])
const cities = ref<CityStat[]>([])
const loading = ref(true)
const selectedCity = ref('')

function weatherEmoji(w: string): string {
  if (!w) return '🌤️'
  if (/晴/.test(w)) return '☀️'
  if (/多云|阴/.test(w)) return '⛅'
  if (/雨|雷/.test(w)) return '🌧️'
  if (/雪/.test(w)) return '❄️'
  return '🌤️'
}

async function fetchRecords() {
  loading.value = true
  try {
    const params: Record<string, any> = { limit: 50 }
    if (selectedCity.value) params.city = selectedCity.value
    const res = await api.get('/weather-records/list', { params })
    records.value = res.data.records ?? []
  } catch { /* ignore */ }
  loading.value = false
}

async function fetchCities() {
  try {
    const res = await api.get('/weather-records/cities')
    cities.value = res.data.cities ?? []
  } catch { /* ignore */ }
}

function filterByCity(city: string) {
  selectedCity.value = selectedCity.value === city ? '' : city
  fetchRecords()
}

onMounted(() => { fetchRecords(); fetchCities() })
</script>

<template>
  <div class="min-h-screen" :class="props.dark ? 'bg-[#212121]' : 'bg-stone-50'">
    <!-- 顶部导航 -->
    <div class="sticky top-0 z-30 flex items-center gap-3 border-b px-5 py-3" :class="props.dark ? 'bg-[#212121] border-stone-700' : 'bg-white border-stone-200'">
      <button class="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 dark:hover:bg-[#2f2f2f]" @click="router.push('/')">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
      </button>
      <h1 class="text-lg font-semibold" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">🌤️ 天气记录</h1>
      <span class="ml-auto text-xs" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">{{ records.length }} 条记录</span>
    </div>

    <div class="mx-auto max-w-3xl px-4 py-6">
      <!-- 城市筛选标签 -->
      <div v-if="cities.length" class="mb-4 flex flex-wrap gap-2">
        <button
          v-for="c in cities" :key="c.city"
          class="rounded-full border px-3 py-1 text-xs transition-colors"
          :class="selectedCity === c.city
            ? 'border-blue-400 bg-blue-50 text-blue-700 dark:border-blue-500 dark:bg-blue-950 dark:text-blue-300'
            : 'border-stone-200 text-stone-500 hover:border-stone-400 dark:border-stone-600 dark:text-stone-400'"
          @click="filterByCity(c.city)"
        >
          {{ c.city }} ({{ c.count }})
        </button>
      </div>

      <div v-if="loading" class="py-12 text-center text-sm text-stone-400">加载中...</div>

      <div v-else-if="records.length === 0" class="py-12 text-center">
        <p class="text-3xl mb-2">🌤️</p>
        <p class="text-sm text-stone-400">暂无天气记录</p>
      </div>

      <div v-else class="space-y-2">
        <div v-for="r in records" :key="r.id"
          class="flex items-center gap-3 rounded-xl border p-3 transition-colors"
          :class="props.dark ? 'border-stone-700 bg-[#2a2a2a]' : 'border-stone-200 bg-white'"
        >
          <span class="text-2xl">{{ weatherEmoji(r.weather) }}</span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="font-medium text-sm" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">{{ r.city }}</span>
              <span class="text-xs" :class="props.dark ? 'text-stone-400' : 'text-stone-500'">{{ r.weather }}</span>
            </div>
            <div class="flex gap-3 mt-0.5 text-[11px]" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">
              <span>🌡️ {{ r.temperature }}°C</span>
              <span v-if="r.humidity">💧 {{ r.humidity }}%</span>
              <span v-if="r.wind_direction">{{ r.wind_direction }}风</span>
            </div>
          </div>
          <span class="text-[10px] shrink-0" :class="props.dark ? 'text-stone-600' : 'text-stone-300'">{{ r.fetched_at }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
