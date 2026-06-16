<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { getDeviceId } from '@/utils/device'

const props = defineProps<{ dark?: boolean; toggleDark?: () => void }>()
const router = useRouter()

interface Stats {
  total_trips: number
  cities_count: number
  total_days: number
  total_budget: number
  top_cities: { city: string; count: number }[]
  composition_dist: { type: string; count: number }[]
}

const stats = ref<Stats | null>(null)
const loading = ref(true)

const compositionLabels: Record<string, string> = {
  solo: '独自出行', couple: '情侣出行', family_child: '带娃家庭',
  family_elder: '带老人家庭', group: '多人结伴',
}

async function fetchStats() {
  loading.value = true
  try {
    const res = await api.get('/travel-stats/overview', { params: { device_id: getDeviceId() } })
    stats.value = res.data
  } catch { /* ignore */ }
  loading.value = false
}

onMounted(fetchStats)
</script>

<template>
  <div class="min-h-screen" :class="props.dark ? 'bg-[#212121]' : 'bg-stone-50'">
    <!-- 顶部导航 -->
    <div class="sticky top-0 z-30 flex items-center gap-3 border-b px-5 py-3" :class="props.dark ? 'bg-[#212121] border-stone-700' : 'bg-white border-stone-200'">
      <button class="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 dark:hover:bg-[#2f2f2f]" @click="router.push('/')">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
      </button>
      <h1 class="text-lg font-semibold" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">📊 出行统计</h1>
    </div>

    <div class="mx-auto max-w-3xl px-4 py-6">
      <div v-if="loading" class="py-12 text-center text-sm text-stone-400">加载中...</div>

      <div v-else-if="!stats || stats.total_trips === 0" class="py-12 text-center">
        <p class="text-3xl mb-2">📊</p>
        <p class="text-sm text-stone-400">暂无出行数据</p>
        <p class="mt-1 text-xs text-stone-300 dark:text-stone-600">规划行程后这里会显示统计信息</p>
      </div>

      <div v-else class="space-y-6">
        <!-- 概览卡片 -->
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div v-for="item in [
            { label: '总行程', value: stats.total_trips, icon: '📋' },
            { label: '城市数', value: stats.cities_count, icon: '📍' },
            { label: '旅行天数', value: stats.total_days, icon: '📅' },
            { label: '总预算', value: `¥${stats.total_budget.toLocaleString()}`, icon: '💰' },
          ]" :key="item.label"
            class="rounded-xl border p-4 text-center"
            :class="props.dark ? 'border-stone-700 bg-[#2a2a2a]' : 'border-stone-200 bg-white'"
          >
            <div class="text-2xl mb-1">{{ item.icon }}</div>
            <div class="text-xl font-bold" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">{{ item.value }}</div>
            <div class="text-xs" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">{{ item.label }}</div>
          </div>
        </div>

        <!-- 最常去的城市 -->
        <div v-if="stats.top_cities.length" class="rounded-xl border p-4" :class="props.dark ? 'border-stone-700 bg-[#2a2a2a]' : 'border-stone-200 bg-white'">
          <h3 class="mb-3 text-sm font-semibold" :class="props.dark ? 'text-stone-300' : 'text-stone-600'">🏆 最常去的城市</h3>
          <div class="space-y-2">
            <div v-for="(c, i) in stats.top_cities" :key="c.city" class="flex items-center gap-3">
              <span class="text-lg">{{ ['🥇','🥈','🥉','4️⃣','5️⃣'][i] }}</span>
              <span class="flex-1 text-sm" :class="props.dark ? 'text-stone-200' : 'text-stone-700'">{{ c.city }}</span>
              <span class="text-xs" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">{{ c.count }}次</span>
            </div>
          </div>
        </div>

        <!-- 人员构成分布 -->
        <div v-if="stats.composition_dist.length" class="rounded-xl border p-4" :class="props.dark ? 'border-stone-700 bg-[#2a2a2a]' : 'border-stone-200 bg-white'">
          <h3 class="mb-3 text-sm font-semibold" :class="props.dark ? 'text-stone-300' : 'text-stone-600'">👥 出行人员统计</h3>
          <div class="flex flex-wrap gap-3">
            <div v-for="c in stats.composition_dist" :key="c.type"
              class="rounded-full border px-3 py-1.5 text-xs"
              :class="props.dark ? 'border-stone-600 text-stone-300' : 'border-stone-200 text-stone-600'"
            >
              {{ compositionLabels[c.type] || c.type }} {{ c.count }}次
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
