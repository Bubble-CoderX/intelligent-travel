<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { getDeviceId } from '@/utils/device'

const props = defineProps<{ dark?: boolean; toggleDark?: () => void }>()
const router = useRouter()

interface Trip {
  id: number
  title: string
  destination: string
  departure_city: string
  days: number
  group_size: number
  composition: string
  budget_total: number
  status: string
  created_at: string
}

const trips = ref<Trip[]>([])
const loading = ref(true)
const total = ref(0)

const statusMap: Record<string, { label: string; color: string }> = {
  planned: { label: '计划中', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  in_progress: { label: '进行中', color: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' },
  completed: { label: '已完成', color: 'bg-stone-100 text-stone-600 dark:bg-stone-700 dark:text-stone-400' },
}

const compositionMap: Record<string, string> = {
  solo: '独自', couple: '情侣', family_child: '带娃', family_elder: '带老人', group: '多人',
}

async function fetchTrips() {
  loading.value = true
  try {
    const res = await api.get(`/trip-history/list`, { params: { device_id: getDeviceId() } })
    trips.value = res.data.trips ?? []
    total.value = res.data.total ?? 0
  } catch { /* ignore */ }
  loading.value = false
}

function viewDetail(id: number) {
  router.push(`/trip-detail/${id}`)
}

function formatDate(d: string) {
  if (!d) return ''
  return d.replace(/-/g, '/')
}

async function markComplete(id: number) {
  try {
    await api.post(`/trip-history/${id}/complete`)
    const trip = trips.value.find(t => t.id === id)
    if (trip) trip.status = 'completed'
  } catch { /* ignore */ }
}

onMounted(fetchTrips)
</script>

<template>
  <div class="min-h-screen" :class="props.dark ? 'bg-[#212121]' : 'bg-stone-50'">
    <!-- 顶部导航 -->
    <div class="sticky top-0 z-30 flex items-center gap-3 border-b px-5 py-3" :class="props.dark ? 'bg-[#212121] border-stone-700' : 'bg-white border-stone-200'">
      <button class="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 dark:hover:bg-[#2f2f2f]" @click="router.push('/')">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
      </button>
      <h1 class="text-lg font-semibold" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">📋 历史行程</h1>
      <span class="ml-auto text-xs" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">共 {{ total }} 条</span>
    </div>

    <!-- 内容 -->
    <div class="mx-auto max-w-3xl px-4 py-6">
      <div v-if="loading" class="py-12 text-center text-sm text-stone-400">加载中...</div>

      <div v-else-if="trips.length === 0" class="py-12 text-center">
        <p class="text-3xl mb-2">📭</p>
        <p class="text-sm text-stone-400">暂无行程记录</p>
        <button class="mt-3 rounded-lg bg-stone-800 px-4 py-2 text-sm text-white dark:bg-stone-200 dark:text-stone-800" @click="router.push('/')">去规划行程</button>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="trip in trips" :key="trip.id"
          class="rounded-xl border p-4 transition-colors cursor-pointer hover:shadow-md"
          :class="props.dark ? 'border-stone-700 bg-[#2a2a2a] hover:bg-[#333]' : 'border-stone-200 bg-white hover:bg-stone-50'"
          @click="viewDetail(trip.id)"
        >
          <div class="flex gap-3">
            <!-- 左侧：标题和信息 -->
            <div class="min-w-0 flex-1">
              <h3 class="font-semibold truncate" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">{{ trip.title || `${trip.destination}${trip.days}日游` }}</h3>
              <div class="mt-1 flex flex-wrap gap-2 text-xs" :class="props.dark ? 'text-stone-400' : 'text-stone-500'">
                <span v-if="trip.departure_city">🚗 {{ trip.departure_city }}→{{ trip.destination }}</span>
                <span v-else>📍 {{ trip.destination }}</span>
                <span>📅 {{ trip.days }}天</span>
                <span>👥 {{ trip.group_size }}人{{ trip.composition ? '(' + (compositionMap[trip.composition] || trip.composition) + ')' : '' }}</span>
                <span v-if="trip.budget_total">💰 ¥{{ Math.round(trip.budget_total) }}</span>
              </div>
              <div class="mt-1 text-xs" :class="props.dark ? 'text-stone-600' : 'text-stone-300'">创建于 {{ formatDate(trip.created_at) }}</div>
            </div>
            <!-- 右侧：状态 + 按钮（固定宽度，不被标题挤压） -->
            <div class="flex flex-col items-end shrink-0 gap-1 ml-2">
              <span class="rounded-full px-2.5 py-0.5 text-[11px] font-medium whitespace-nowrap" :class="statusMap[trip.status]?.color">
                {{ statusMap[trip.status]?.label || trip.status }}
              </span>
              <button v-if="trip.status === 'planned'" class="text-[10px] text-green-500 hover:text-green-700 whitespace-nowrap" @click.stop="markComplete(trip.id)">✓完成</button>
            </div>
          </div>
          <div class="flex flex-wrap gap-2 text-xs mt-2" :class="props.dark ? 'text-stone-400' : 'text-stone-500'">
            <span>创建于 {{ formatDate(trip.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
