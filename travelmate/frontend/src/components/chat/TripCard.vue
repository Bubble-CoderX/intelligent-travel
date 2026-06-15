<script setup lang="ts">
import { ref, computed } from 'vue'

// ── Props ────────────────────────────────────────────
const props = defineProps<{
  tripPlan: TripPlan | null
  safetyWarning?: string
  fallbackSummary?: string
  tripStyle?: string
}>()

const emit = defineEmits<{
  switchStyle: []
}>()

// ── 行程风格标签 ──────────────────────────────────────
const STYLE_LABELS: Record<string, { emoji: string; label: string }> = {
  compact: { emoji: '⚡', label: '紧凑打卡型' },
  leisure: { emoji: '🌴', label: '休闲度假型' },
  culture: { emoji: '📚', label: '深度文化型' },
}

const currentStyleLabel = computed(() => {
  if (!props.tripStyle || props.tripStyle === 'default') return null
  return STYLE_LABELS[props.tripStyle] ?? null
})

// ── Types ────────────────────────────────────────────
interface SpotItem {
  name: string
  start_time?: string
  end_time?: string
  description?: string
  tips?: string
  location?: string
  address?: string
  estimated_cost?: number
}

interface MealItem {
  meal_type: string
  name: string
  notes?: string
  estimated_cost?: number
}

interface TransportItem {
  mode: string
  from_place?: string
  to_place?: string
  duration?: string
  estimated_cost?: number
}

interface HotelItem {
  name: string
  level?: string
  location?: string
  estimated_cost?: number
}

interface DayPlan {
  day_index: number
  theme?: string
  spots?: SpotItem[]
  meals?: MealItem[]
  transport?: TransportItem[]
  hotel?: HotelItem | null
}

interface BudgetBreakdown {
  transport: number
  hotel: number
  meals: number
  tickets: number
  other: number
  total: number
}

interface TripPlan {
  trip_id: string
  destination: string
  summary: string
  days: DayPlan[]
  estimated_budget?: number
  budget_breakdown?: BudgetBreakdown | null
  food_summary?: string
  transport_summary?: string
  accommodation_summary?: string
  tips?: string[]
}

// ── State ────────────────────────────────────────────
const activeTab = ref<string>('overview')
const bottomPanel = ref<'transport' | 'food' | 'accommodation' | null>(null)
const showExportMenu = ref(false)
const checklist = ref<{ categories: { name: string; icon: string; items: any[] }[] } | null>(null)
const loadingChecklist = ref(false)

async function genChecklist() {
  if (!props.tripPlan?.trip_id || loadingChecklist.value) return
  loadingChecklist.value = true
  try {
    const res = await fetch(`http://localhost:8000/trip/${props.tripPlan.trip_id}/checklist`, { signal: AbortSignal.timeout(15000) })
    const data = await res.json()
    checklist.value = data.checklist
  } catch { /* 静默失败 */ }
  finally { loadingChecklist.value = false }
}

function exportJSON() {
  if (!props.tripPlan?.trip_id) return
  const blob = new Blob([JSON.stringify(props.tripPlan, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.tripPlan.trip_id}.json`
  a.click()
  URL.revokeObjectURL(url)
  showExportMenu.value = false
}

// ── Computed ─────────────────────────────────────────
const tabKeys = computed(() => {
  if (!props.tripPlan?.days?.length) return ['overview']
  return ['overview', ...props.tripPlan.days.map((_, i) => `day${i}`)]
})

const currentDay = computed(() => {
  if (activeTab.value === 'overview') return null
  const idx = parseInt(activeTab.value.replace('day', ''))
  return props.tripPlan?.days?.[idx] ?? null
})

const allTransport = computed(() => {
  if (!props.tripPlan?.days) return []
  return props.tripPlan.days.flatMap(d => d.transport ?? [])
})

const allMeals = computed(() => {
  if (!props.tripPlan?.days) return []
  return props.tripPlan.days.flatMap(d => d.meals ?? [])
})

const allHotels = computed(() => {
  if (!props.tripPlan?.days) return []
  return props.tripPlan.days
    .map(d => d.hotel)
    .filter(Boolean) as HotelItem[]
})

const budgetItems = computed(() => {
  const b = props.tripPlan?.budget_breakdown
  if (!b) return []
  return [
    { label: '交通', icon: '🚗', value: b.transport },
    { label: '住宿', icon: '🏨', value: b.hotel },
    { label: '餐饮', icon: '🍜', value: b.meals },
    { label: '门票', icon: '🎫', value: b.tickets },
    { label: '其他', icon: '📦', value: b.other },
  ]
})

const maxBudget = computed(() => {
  return Math.max(...budgetItems.value.map(i => i.value), 1)
})

// ── Helpers ──────────────────────────────────────────
const transportEmoji = (mode: string) => {
  if (/打车|出租|的士/.test(mode)) return '🚕'
  if (/公交|地铁|乘车/.test(mode)) return '🚌'
  if (/步行|徒步/.test(mode)) return '🚶'
  if (/高铁|火车|动车/.test(mode)) return '🚄'
  return '🚗'
}

const mealEmoji = (type: string) => {
  if (/早餐/.test(type)) return '🥐'
  if (/午餐/.test(type)) return '🍱'
  if (/晚餐/.test(type)) return '🌙'
  return '🍴'
}
</script>

<template>
  <!-- fallback: 旧版 Markdown 卡片（无结构化数据时） -->
  <div v-if="!tripPlan && fallbackSummary" class="my-2 rounded-xl border border-stone-200 bg-stone-50 p-5 shadow-sm dark:border-stone-700 dark:bg-[#1a1a1a]">
    <p class="text-sm text-gray-600 dark:text-stone-300">目的地：{{ safetyWarning ? '' : '' }}</p>
    <div class="prose prose-sm max-w-none text-sm leading-relaxed text-gray-700 dark:text-stone-200" v-html="fallbackSummary" />
    <div v-if="safetyWarning" class="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
      ⚠️ {{ safetyWarning }}
    </div>
  </div>

  <!-- 结构化 TripCard -->
  <div v-else-if="tripPlan" class="my-2 overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm dark:border-stone-700 dark:bg-[#1a1a1a]" @click="showExportMenu = false">
    <!-- Header -->
    <div class="bg-gradient-to-r from-stone-700 to-stone-600 px-5 py-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-bold text-white">{{ tripPlan.destination }} · {{ tripPlan.days?.length ?? 0 }} 日游</h3>
          <div class="mt-1 flex items-center gap-2">
            <p v-if="!currentStyleLabel" class="text-sm text-stone-200">{{ tripPlan.summary }}</p>
            <span
              v-if="currentStyleLabel"
              class="inline-flex items-center gap-1 rounded-full bg-white/25 px-2.5 py-0.5 text-xs font-medium text-white"
            >
              {{ currentStyleLabel.emoji }} {{ currentStyleLabel.label }}
            </span>
            <button
              class="inline-flex items-center gap-1 rounded-full bg-white/20 px-2.5 py-0.5 text-xs text-white/80 transition-colors hover:bg-white/30 hover:text-white"
              @click.stop="emit('switchStyle')"
            >
              🔄 换种风格
            </button>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span class="rounded-full bg-white/20 px-3 py-1 text-xs font-medium text-white">
            {{ tripPlan.days?.length ?? 0 }} 天
          </span>
          <div v-if="tripPlan.trip_id" class="relative">
            <button
              class="rounded-lg bg-white/20 p-1.5 text-white transition-colors hover:bg-white/30"
              @click.stop="showExportMenu = !showExportMenu"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
            </button>
            <div
              v-if="showExportMenu"
              class="absolute right-0 top-full z-20 mt-1 min-w-[120px] rounded-lg border border-stone-200 bg-white py-1 shadow-lg dark:border-stone-700 dark:bg-[#2f2f2f]"
            >
              <a
                :href="`http://localhost:8000/trip/${tripPlan.trip_id}/export?format=pdf`"
                target="_blank"
                class="flex items-center gap-2 px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-50 dark:text-stone-200 dark:hover:bg-[#3a3a3a]"
                @click="showExportMenu = false"
              >
                📄 导出 PDF
              </a>
              <button
                class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-stone-700 hover:bg-stone-50 dark:text-stone-200 dark:hover:bg-[#3a3a3a]"
                @click="exportJSON"
              >
                📋 导出 JSON
              </button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="safetyWarning" class="mt-3 rounded-lg bg-red-50/90 px-3 py-2 text-xs font-medium text-red-700 dark:bg-red-950/90 dark:text-red-300">
        ⚠️ {{ safetyWarning }}
      </div>
      <!-- 清单按钮 -->
      <button
        v-if="!checklist"
        :disabled="loadingChecklist"
        class="mt-3 inline-flex items-center gap-1 rounded-lg bg-white/20 px-3 py-1.5 text-xs text-white transition-colors hover:bg-white/30 disabled:opacity-50"
        @click.stop="genChecklist"
      >
        {{ loadingChecklist ? '生成中...' : '📋 生成准备清单' }}
      </button>
    </div>

    <!-- 准备清单 -->
    <div v-if="checklist" class="border-b border-stone-100 px-5 py-4 dark:border-stone-800">
      <h4 class="mb-3 text-sm font-semibold text-stone-700 dark:text-stone-200">📋 旅行准备清单</h4>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div v-for="(cat, ci) in checklist.categories" :key="ci" class="rounded-lg bg-stone-50 p-3 dark:bg-[#1e1e1e]">
          <h5 class="mb-1.5 text-xs font-medium text-stone-600 dark:text-stone-300">{{ cat.icon }} {{ cat.name }}</h5>
          <ul class="space-y-0.5">
            <li v-for="(item, ii) in cat.items" :key="ii" class="text-[11px] text-stone-500 dark:text-stone-400">
              <template v-if="typeof item === 'object'">
                <span v-if="item.essential" class="text-red-400">★</span>
                {{ item.name }}
                <span v-if="item.note" class="text-stone-400 dark:text-stone-500">（{{ item.note }}）</span>
              </template>
              <template v-else>• {{ item }}</template>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Tab Bar -->
    <div class="flex overflow-x-auto border-b border-stone-100 bg-stone-50/50 dark:border-stone-800 dark:bg-[#1e1e1e]/50">
      <button
        v-for="(key, i) in tabKeys"
        :key="key"
        class="shrink-0 px-4 py-3 text-sm font-medium transition-colors"
        :class="activeTab === key
          ? 'border-b-2 border-stone-700 text-stone-700 dark:border-stone-300 dark:text-stone-200'
          : 'text-stone-500 hover:text-stone-700 dark:text-stone-400 dark:hover:text-stone-200'"
        @click="activeTab = key"
      >
        {{ i === 0 ? '行程总览' : `Day ${i}` }}
      </button>
    </div>

    <!-- Tab Content -->
    <div class="max-h-[500px] overflow-y-auto px-5 py-4">
      <!-- 行程总览 -->
      <div v-if="activeTab === 'overview'" class="space-y-4">
        <p class="text-sm leading-relaxed text-stone-700 dark:text-stone-200">{{ tripPlan.summary }}</p>

        <!-- 预算分解 -->
        <div v-if="tripPlan.budget_breakdown" class="rounded-xl bg-stone-50 p-4 dark:bg-[#1e1e1e]">
          <h4 class="mb-3 text-sm font-semibold text-stone-700 dark:text-stone-200">💰 预算估算</h4>
          <div class="space-y-2">
            <div v-for="item in budgetItems" :key="item.label" class="flex items-center gap-3 text-sm">
              <span class="w-8 text-center">{{ item.icon }}</span>
              <span class="w-10 text-right text-stone-500 dark:text-stone-400">{{ item.label }}</span>
              <div class="flex-1 h-2 rounded-full bg-stone-200 dark:bg-stone-700">
                <div
                  class="h-2 rounded-full bg-stone-500 dark:bg-stone-400 transition-all"
                  :style="{ width: (item.value / maxBudget * 100) + '%' }"
                />
              </div>
              <span class="w-16 text-right font-medium text-stone-700 dark:text-stone-200">¥{{ item.value }}</span>
            </div>
          </div>
          <div class="mt-3 border-t border-stone-200 pt-3 text-right font-bold text-stone-700 dark:border-stone-700 dark:text-stone-200">
            总计 ¥{{ tripPlan.budget_breakdown.total || tripPlan.estimated_budget || 0 }}
          </div>
        </div>

        <!-- 旅行贴士 -->
        <div v-if="tripPlan.tips?.length" class="rounded-xl bg-sky-50 p-4 dark:bg-sky-950">
          <h4 class="mb-2 text-sm font-semibold text-stone-700 dark:text-stone-200">💡 旅行贴士</h4>
          <ul class="space-y-1">
            <li v-for="(tip, i) in tripPlan.tips" :key="i" class="flex items-start gap-2 text-sm text-stone-600 dark:text-stone-300">
              <span class="mt-0.5 shrink-0 text-sky-400 dark:text-sky-300">•</span>
              {{ tip }}
            </li>
          </ul>
        </div>
      </div>

      <!-- Day N Tab -->
      <div v-else class="space-y-4">
        <!-- 主题标题 -->
        <div v-if="currentDay?.theme" class="rounded-lg bg-stone-50 px-4 py-3 text-center dark:bg-[#1e1e1e]">
          <span class="text-sm font-semibold text-stone-700 dark:text-stone-200">{{ currentDay.theme }}</span>
        </div>

        <!-- 景点时间线 -->
        <div class="relative space-y-4">
          <div v-for="(spot, si) in (currentDay?.spots ?? [])" :key="si" class="relative">
            <!-- 时间线连接线 -->
            <div
              v-if="si < (currentDay?.spots?.length ?? 0) - 1"
              class="absolute left-4 top-10 h-full w-0.5 bg-stone-200 dark:bg-stone-700"
            />

            <div class="flex gap-3">
              <!-- 时间戳 -->
              <div class="shrink-0 text-right" style="width: 64px">
                <div v-if="spot.start_time" class="text-xs font-medium text-stone-600 dark:text-stone-300">{{ spot.start_time }}</div>
                <div v-if="spot.end_time" class="text-[10px] text-stone-400 dark:text-stone-500">{{ spot.end_time }}</div>
              </div>

              <!-- 时间线圆点 -->
              <div class="relative flex flex-col items-center">
                <div class="z-10 mt-1 h-3 w-3 rounded-full border-2 border-stone-400 bg-white dark:border-stone-500 dark:bg-[#1a1a1a]" />
              </div>

              <!-- 景点卡片 -->
              <div class="flex-1 rounded-xl border border-stone-100 bg-stone-50/50 p-3 dark:border-stone-800 dark:bg-[#1e1e1e]/50">
                <h5 class="text-sm font-semibold text-stone-800 dark:text-stone-100">{{ spot.name }}</h5>
                <p v-if="spot.description" class="mt-1 text-xs leading-relaxed text-stone-600 dark:text-stone-300">{{ spot.description }}</p>
                <div v-if="spot.address" class="mt-2 flex items-center gap-1 text-[11px] text-stone-400 dark:text-stone-500">
                  📍 {{ spot.address }}
                </div>
                <div v-if="spot.tips" class="mt-2 rounded-lg bg-stone-100 px-3 py-2 text-xs text-stone-600 dark:bg-[#2a2a2a] dark:text-stone-300">
                  💡 {{ spot.tips }}
                </div>
              </div>
            </div>

            <!-- 景点间交通 -->
            <div
              v-if="si < (currentDay?.transport?.length ?? 0) && currentDay?.transport?.[si]"
              class="ml-4 mt-2 flex items-center gap-2 rounded-lg border border-dashed border-stone-200 px-3 py-2 dark:border-stone-700"
            >
              <span>{{ transportEmoji(currentDay.transport![si].mode) }}</span>
              <span class="text-xs text-stone-500 dark:text-stone-400">{{ currentDay.transport![si].mode }}</span>
              <span v-if="currentDay.transport![si].from_place && currentDay.transport![si].to_place" class="text-xs text-stone-400 dark:text-stone-500">
                {{ currentDay.transport![si].from_place }} → {{ currentDay.transport![si].to_place }}
              </span>
              <span v-if="currentDay.transport![si].duration" class="text-xs text-stone-400 dark:text-stone-500">
                {{ currentDay.transport![si].duration }}
              </span>
              <span v-if="currentDay.transport![si].estimated_cost" class="ml-auto text-xs font-medium text-stone-600 dark:text-stone-300">
                ¥{{ currentDay.transport![si].estimated_cost }}
              </span>
            </div>
          </div>
        </div>

        <!-- 餐饮推荐 -->
        <div v-if="(currentDay?.meals?.length ?? 0) > 0" class="rounded-xl bg-emerald-50 p-4 dark:bg-emerald-950">
          <h4 class="mb-2 text-sm font-semibold text-stone-700 dark:text-stone-200">🍴 餐饮推荐</h4>
          <div class="space-y-2">
            <div v-for="(meal, mi) in currentDay!.meals" :key="mi" class="flex items-start gap-3 rounded-lg bg-white p-3 text-sm dark:bg-[#1e1e1e]">
              <span class="text-lg">{{ mealEmoji(meal.meal_type) }}</span>
              <div class="flex-1">
                <div class="flex items-center justify-between">
                  <span class="font-medium text-stone-700 dark:text-stone-200">{{ meal.name }}</span>
                  <span class="text-xs text-stone-400 dark:text-stone-500">{{ meal.meal_type }}</span>
                </div>
                <p v-if="meal.notes" class="mt-0.5 text-xs text-stone-500 dark:text-stone-400">{{ meal.notes }}</p>
              </div>
              <span v-if="meal.estimated_cost" class="text-xs font-medium text-stone-600 dark:text-stone-300">¥{{ meal.estimated_cost }}</span>
            </div>
          </div>
        </div>

        <!-- 住宿建议 -->
        <div v-if="currentDay?.hotel" class="rounded-xl bg-stone-50 p-4 dark:bg-[#1e1e1e]">
          <h4 class="mb-2 text-sm font-semibold text-stone-700 dark:text-stone-200">🏨 住宿建议</h4>
          <div class="rounded-lg bg-white p-3 text-sm dark:bg-[#1a1a1a]">
            <span class="font-medium text-stone-700 dark:text-stone-200">{{ currentDay.hotel.name }}</span>
            <span v-if="currentDay.hotel.level" class="ml-2 text-xs text-stone-400 dark:text-stone-500">{{ currentDay.hotel.level }}</span>
            <div v-if="currentDay.hotel.location" class="mt-1 text-xs text-stone-500 dark:text-stone-400">📍 {{ currentDay.hotel.location }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Nav -->
    <div class="flex border-t border-stone-100 dark:border-stone-800">
      <button
        class="flex flex-1 items-center justify-center gap-1.5 py-3 text-xs font-medium transition-colors"
        :class="bottomPanel === 'transport' ? 'bg-stone-100 text-stone-700 dark:bg-[#2a2a2a] dark:text-stone-200' : 'text-stone-500 hover:bg-stone-50 dark:text-stone-400 dark:hover:bg-[#1e1e1e]'"
        @click="bottomPanel = bottomPanel === 'transport' ? null : 'transport'"
      >
        🚗 交通
      </button>
      <button
        class="flex flex-1 items-center justify-center gap-1.5 border-x border-stone-100 py-3 text-xs font-medium transition-colors dark:border-stone-800"
        :class="bottomPanel === 'food' ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400' : 'text-stone-500 hover:bg-stone-50 dark:text-stone-400 dark:hover:bg-[#1e1e1e]'"
        @click="bottomPanel = bottomPanel === 'food' ? null : 'food'"
      >
        🍜 美食
      </button>
      <button
        class="flex flex-1 items-center justify-center gap-1.5 py-3 text-xs font-medium transition-colors"
        :class="bottomPanel === 'accommodation' ? 'bg-sky-50 text-sky-600 dark:bg-sky-950 dark:text-sky-400' : 'text-stone-500 hover:bg-stone-50 dark:text-stone-400 dark:hover:bg-[#1e1e1e]'"
        @click="bottomPanel = bottomPanel === 'accommodation' ? null : 'accommodation'"
      >
        🏨 住宿
      </button>
    </div>

    <!-- Bottom Panel -->
    <div v-if="bottomPanel" class="max-h-[200px] overflow-y-auto border-t border-stone-100 bg-stone-50 px-5 py-3 dark:border-stone-800 dark:bg-[#1e1e1e]">
      <!-- 交通汇总 -->
      <div v-if="bottomPanel === 'transport'">
        <p v-if="tripPlan.transport_summary" class="mb-2 text-xs text-stone-600 dark:text-stone-300">{{ tripPlan.transport_summary }}</p>
        <div v-if="allTransport.length" class="space-y-2">
          <div v-for="(t, i) in allTransport" :key="i" class="flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-xs dark:bg-[#1a1a1a]">
            <span>{{ transportEmoji(t.mode) }}</span>
            <span class="text-stone-600 dark:text-stone-300">{{ t.mode }}</span>
            <span v-if="t.from_place && t.to_place" class="text-stone-400 dark:text-stone-500">{{ t.from_place }} → {{ t.to_place }}</span>
            <span v-if="t.duration" class="text-stone-400 dark:text-stone-500">{{ t.duration }}</span>
            <span v-if="t.estimated_cost" class="ml-auto font-medium text-stone-600 dark:text-stone-300">¥{{ t.estimated_cost }}</span>
          </div>
        </div>
        <p v-else class="text-xs text-stone-400 dark:text-stone-500">暂无交通信息</p>
      </div>

      <!-- 美食汇总 -->
      <div v-if="bottomPanel === 'food'">
        <p v-if="tripPlan.food_summary" class="mb-2 text-xs text-stone-600 dark:text-stone-300">{{ tripPlan.food_summary }}</p>
        <div v-if="allMeals.length" class="space-y-2">
          <div v-for="(m, i) in allMeals" :key="i" class="flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-xs dark:bg-[#1a1a1a]">
            <span>{{ mealEmoji(m.meal_type) }}</span>
            <span class="font-medium text-stone-700 dark:text-stone-200">{{ m.name }}</span>
            <span class="text-stone-400 dark:text-stone-500">{{ m.meal_type }}</span>
            <span v-if="m.estimated_cost" class="ml-auto text-stone-500 dark:text-stone-400">¥{{ m.estimated_cost }}</span>
          </div>
        </div>
        <p v-else class="text-xs text-stone-400 dark:text-stone-500">暂无美食信息</p>
      </div>

      <!-- 住宿汇总 -->
      <div v-if="bottomPanel === 'accommodation'">
        <p v-if="tripPlan.accommodation_summary" class="mb-2 text-xs text-stone-600 dark:text-stone-300">{{ tripPlan.accommodation_summary }}</p>
        <div v-if="allHotels.length" class="space-y-2">
          <div v-for="(h, i) in allHotels" :key="i" class="rounded-lg bg-white px-3 py-2 text-xs dark:bg-[#1a1a1a]">
            <span class="font-medium text-stone-700 dark:text-stone-200">{{ h.name }}</span>
            <span v-if="h.level" class="ml-2 text-stone-400 dark:text-stone-500">{{ h.level }}</span>
            <span v-if="h.estimated_cost" class="ml-2 text-stone-600 dark:text-stone-300">¥{{ h.estimated_cost }}</span>
            <div v-if="h.location" class="mt-1 text-stone-400 dark:text-stone-500">📍 {{ h.location }}</div>
          </div>
        </div>
        <p v-else class="text-xs text-stone-400 dark:text-stone-500">暂无住宿信息</p>
      </div>
    </div>
  </div>
</template>
