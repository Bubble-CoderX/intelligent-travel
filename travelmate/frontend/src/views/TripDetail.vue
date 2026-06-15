<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'

const route = useRoute()
const router = useRouter()
const props = defineProps<{ dark?: boolean; toggleDark?: () => void }>()

const trip = ref<any>(null)
const loading = ref(true)
const error = ref('')

async function fetchTrip() {
  const id = route.params.id
  try {
    const res = await api.get(`/trip-history/${id}`)
    trip.value = res.data
  } catch (e: any) {
    error.value = e.response?.data?.detail || '加载失败'
  }
  loading.value = false
}

onMounted(fetchTrip)
</script>

<template>
  <div class="min-h-screen" :class="props.dark ? 'bg-[#212121]' : 'bg-stone-50'">
    <div class="sticky top-0 z-30 flex items-center gap-3 border-b px-5 py-3" :class="props.dark ? 'bg-[#212121] border-stone-700' : 'bg-white border-stone-200'">
      <button class="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 dark:hover:bg-[#2f2f2f]" @click="router.back()">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
      </button>
      <h1 class="text-lg font-semibold" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">行程详情</h1>
    </div>

    <div class="mx-auto max-w-3xl px-4 py-6">
      <div v-if="loading" class="py-12 text-center text-sm text-stone-400">加载中...</div>
      <div v-else-if="error" class="py-12 text-center text-sm text-red-500">{{ error }}</div>
      <div v-else-if="trip?.itinerary">
        <!-- 简要信息 -->
        <div class="mb-4 rounded-xl border p-4" :class="props.dark ? 'border-stone-700 bg-[#2a2a2a]' : 'border-stone-200 bg-white'">
          <h2 class="font-semibold" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">{{ trip.title }}</h2>
          <div class="mt-2 flex flex-wrap gap-3 text-xs" :class="props.dark ? 'text-stone-400' : 'text-stone-500'">
            <span>📍 {{ trip.destination }}</span>
            <span>📅 {{ trip.days }}天</span>
            <span v-if="trip.budget_total">💰 ¥{{ Math.round(trip.budget_total) }}</span>
          </div>
        </div>

        <!-- 每日行程 -->
        <div v-for="(day, idx) in trip.itinerary.days" :key="idx" class="mb-4">
          <h3 class="mb-2 font-semibold" :class="props.dark ? 'text-stone-300' : 'text-stone-700'">
            Day {{ day.day_index || idx + 1 }}：{{ day.theme || '' }}
          </h3>
          <div class="space-y-2">
            <div v-for="(spot, si) in (day.spots || [])" :key="si"
              class="rounded-lg border p-3"
              :class="props.dark ? 'border-stone-700 bg-[#2a2a2a]' : 'border-stone-100 bg-white'"
            >
              <div class="flex items-center justify-between">
                <span class="text-xs" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">{{ spot.start_time }}-{{ spot.end_time }}</span>
              </div>
              <div class="font-medium" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">{{ spot.name }}</div>
              <div class="mt-1 text-xs" :class="props.dark ? 'text-stone-400' : 'text-stone-500'">{{ spot.description }}</div>
              <div v-if="spot.tips" class="mt-1 text-xs text-amber-600 dark:text-amber-400">💡 {{ spot.tips }}</div>
            </div>
            <!-- 餐饮 -->
            <div v-for="(meal, mi) in (day.meals || [])" :key="'m'+mi"
              class="rounded-lg border border-green-100 bg-green-50 p-3 dark:border-green-900 dark:bg-green-950"
            >
              <span class="text-xs font-medium text-green-700 dark:text-green-400">{{ meal.meal_type }}</span>
              <span class="ml-2 text-sm" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">{{ meal.name }}</span>
              <span v-if="meal.estimated_cost" class="ml-2 text-xs text-stone-400">¥{{ meal.estimated_cost }}</span>
            </div>
          </div>
        </div>

        <!-- Tips -->
        <div v-if="trip.itinerary.tips?.length" class="rounded-xl border p-4" :class="props.dark ? 'border-stone-700 bg-[#2a2a2a]' : 'border-stone-200 bg-white'">
          <h3 class="mb-2 font-semibold" :class="props.dark ? 'text-stone-300' : 'text-stone-700'">💡 旅行贴士</h3>
          <ul class="space-y-1">
            <li v-for="(tip, ti) in trip.itinerary.tips" :key="ti" class="text-xs" :class="props.dark ? 'text-stone-400' : 'text-stone-500'">• {{ tip }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
