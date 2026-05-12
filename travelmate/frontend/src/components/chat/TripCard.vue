<script setup lang="ts">
import { ref, computed } from 'vue'

// ── Props ────────────────────────────────────────────
const props = defineProps<{
  tripPlan: TripPlan | null
  safetyWarning?: string
  fallbackSummary?: string
}>()

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
  <div v-if="!tripPlan && fallbackSummary" class="my-2 rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50 to-white p-5 shadow-sm">
    <p class="text-sm text-gray-600">目的地：{{ safetyWarning ? '' : '' }}</p>
    <div class="prose prose-sm max-w-none text-sm leading-relaxed text-gray-700" v-html="fallbackSummary" />
    <div v-if="safetyWarning" class="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
      ⚠️ {{ safetyWarning }}
    </div>
  </div>

  <!-- 结构化 TripCard -->
  <div v-else-if="tripPlan" class="my-2 overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
    <!-- Header -->
    <div class="bg-gradient-to-r from-amber-500 to-orange-400 px-5 py-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-bold text-white">{{ tripPlan.destination }} · {{ tripPlan.days?.length ?? 0 }} 日游</h3>
          <p class="mt-1 text-sm text-amber-50">{{ tripPlan.summary }}</p>
        </div>
        <span class="rounded-full bg-white/20 px-3 py-1 text-xs font-medium text-white">
          {{ tripPlan.days?.length ?? 0 }} 天
        </span>
      </div>
      <div v-if="safetyWarning" class="mt-3 rounded-lg bg-red-50/90 px-3 py-2 text-xs font-medium text-red-700">
        ⚠️ {{ safetyWarning }}
      </div>
    </div>

    <!-- Tab Bar -->
    <div class="flex overflow-x-auto border-b border-stone-100 bg-stone-50/50">
      <button
        v-for="(key, i) in tabKeys"
        :key="key"
        class="shrink-0 px-4 py-3 text-sm font-medium transition-colors"
        :class="activeTab === key
          ? 'border-b-2 border-amber-500 text-amber-600'
          : 'text-stone-500 hover:text-stone-700'"
        @click="activeTab = key"
      >
        {{ i === 0 ? '行程总览' : `Day ${i}` }}
      </button>
    </div>

    <!-- Tab Content -->
    <div class="max-h-[500px] overflow-y-auto px-5 py-4">
      <!-- 行程总览 -->
      <div v-if="activeTab === 'overview'" class="space-y-4">
        <p class="text-sm leading-relaxed text-stone-700">{{ tripPlan.summary }}</p>

        <!-- 预算分解 -->
        <div v-if="tripPlan.budget_breakdown" class="rounded-xl bg-amber-50 p-4">
          <h4 class="mb-3 text-sm font-semibold text-stone-700">💰 预算估算</h4>
          <div class="space-y-2">
            <div v-for="item in budgetItems" :key="item.label" class="flex items-center gap-3 text-sm">
              <span class="w-8 text-center">{{ item.icon }}</span>
              <span class="w-10 text-right text-stone-500">{{ item.label }}</span>
              <div class="flex-1 h-2 rounded-full bg-amber-100">
                <div
                  class="h-2 rounded-full bg-amber-400 transition-all"
                  :style="{ width: (item.value / maxBudget * 100) + '%' }"
                />
              </div>
              <span class="w-16 text-right font-medium text-stone-700">¥{{ item.value }}</span>
            </div>
          </div>
          <div class="mt-3 border-t border-amber-200 pt-3 text-right font-bold text-amber-600">
            总计 ¥{{ tripPlan.budget_breakdown.total || tripPlan.estimated_budget || 0 }}
          </div>
        </div>

        <!-- 旅行贴士 -->
        <div v-if="tripPlan.tips?.length" class="rounded-xl bg-sky-50 p-4">
          <h4 class="mb-2 text-sm font-semibold text-stone-700">💡 旅行贴士</h4>
          <ul class="space-y-1">
            <li v-for="(tip, i) in tripPlan.tips" :key="i" class="flex items-start gap-2 text-sm text-stone-600">
              <span class="mt-0.5 shrink-0 text-sky-400">•</span>
              {{ tip }}
            </li>
          </ul>
        </div>
      </div>

      <!-- Day N Tab -->
      <div v-else class="space-y-4">
        <!-- 主题标题 -->
        <div v-if="currentDay?.theme" class="rounded-lg bg-stone-50 px-4 py-3 text-center">
          <span class="text-sm font-semibold text-stone-700">{{ currentDay.theme }}</span>
        </div>

        <!-- 景点时间线 -->
        <div class="relative space-y-4">
          <div v-for="(spot, si) in (currentDay?.spots ?? [])" :key="si" class="relative">
            <!-- 时间线连接线 -->
            <div
              v-if="si < (currentDay?.spots?.length ?? 0) - 1"
              class="absolute left-4 top-10 h-full w-0.5 bg-amber-200"
            />

            <div class="flex gap-3">
              <!-- 时间戳 -->
              <div class="shrink-0 text-right" style="width: 64px">
                <div v-if="spot.start_time" class="text-xs font-medium text-amber-600">{{ spot.start_time }}</div>
                <div v-if="spot.end_time" class="text-[10px] text-stone-400">{{ spot.end_time }}</div>
              </div>

              <!-- 时间线圆点 -->
              <div class="relative flex flex-col items-center">
                <div class="z-10 mt-1 h-3 w-3 rounded-full border-2 border-amber-400 bg-white" />
              </div>

              <!-- 景点卡片 -->
              <div class="flex-1 rounded-xl border border-stone-100 bg-stone-50/50 p-3">
                <h5 class="text-sm font-semibold text-stone-800">{{ spot.name }}</h5>
                <p v-if="spot.description" class="mt-1 text-xs leading-relaxed text-stone-600">{{ spot.description }}</p>

                <!-- 位置 -->
                <div v-if="spot.address" class="mt-2 flex items-center gap-1 text-[11px] text-stone-400">
                  📍 {{ spot.address }}
                </div>

                <!-- 贴士 -->
                <div v-if="spot.tips" class="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
                  💡 {{ spot.tips }}
                </div>
              </div>
            </div>

            <!-- 景点间交通 -->
            <div
              v-if="si < (currentDay?.transport?.length ?? 0) && currentDay?.transport?.[si]"
              class="ml-4 mt-2 flex items-center gap-2 rounded-lg border border-dashed border-stone-200 px-3 py-2"
            >
              <span>{{ transportEmoji(currentDay.transport![si].mode) }}</span>
              <span class="text-xs text-stone-500">{{ currentDay.transport![si].mode }}</span>
              <span v-if="currentDay.transport![si].from_place && currentDay.transport![si].to_place" class="text-xs text-stone-400">
                {{ currentDay.transport![si].from_place }} → {{ currentDay.transport![si].to_place }}
              </span>
              <span v-if="currentDay.transport![si].duration" class="text-xs text-stone-400">
                {{ currentDay.transport![si].duration }}
              </span>
              <span v-if="currentDay.transport![si].estimated_cost" class="ml-auto text-xs font-medium text-stone-600">
                ¥{{ currentDay.transport![si].estimated_cost }}
              </span>
            </div>
          </div>
        </div>

        <!-- 餐饮推荐 -->
        <div v-if="(currentDay?.meals?.length ?? 0) > 0" class="rounded-xl bg-emerald-50 p-4">
          <h4 class="mb-2 text-sm font-semibold text-stone-700">🍴 餐饮推荐</h4>
          <div class="space-y-2">
            <div v-for="(meal, mi) in currentDay!.meals" :key="mi" class="flex items-start gap-3 rounded-lg bg-white p-3 text-sm">
              <span class="text-lg">{{ mealEmoji(meal.meal_type) }}</span>
              <div class="flex-1">
                <div class="flex items-center justify-between">
                  <span class="font-medium text-stone-700">{{ meal.name }}</span>
                  <span class="text-xs text-stone-400">{{ meal.meal_type }}</span>
                </div>
                <p v-if="meal.notes" class="mt-0.5 text-xs text-stone-500">{{ meal.notes }}</p>
              </div>
              <span v-if="meal.estimated_cost" class="text-xs font-medium text-stone-600">¥{{ meal.estimated_cost }}</span>
            </div>
          </div>
        </div>

        <!-- 住宿建议 -->
        <div v-if="currentDay?.hotel" class="rounded-xl bg-stone-50 p-4">
          <h4 class="mb-2 text-sm font-semibold text-stone-700">🏨 住宿建议</h4>
          <div class="rounded-lg bg-white p-3 text-sm">
            <span class="font-medium text-stone-700">{{ currentDay.hotel.name }}</span>
            <span v-if="currentDay.hotel.level" class="ml-2 text-xs text-stone-400">{{ currentDay.hotel.level }}</span>
            <div v-if="currentDay.hotel.location" class="mt-1 text-xs text-stone-500">📍 {{ currentDay.hotel.location }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Nav -->
    <div class="flex border-t border-stone-100">
      <button
        class="flex flex-1 items-center justify-center gap-1.5 py-3 text-xs font-medium transition-colors"
        :class="bottomPanel === 'transport' ? 'bg-amber-50 text-amber-600' : 'text-stone-500 hover:bg-stone-50'"
        @click="bottomPanel = bottomPanel === 'transport' ? null : 'transport'"
      >
        🚗 交通
      </button>
      <button
        class="flex flex-1 items-center justify-center gap-1.5 border-x border-stone-100 py-3 text-xs font-medium transition-colors"
        :class="bottomPanel === 'food' ? 'bg-emerald-50 text-emerald-600' : 'text-stone-500 hover:bg-stone-50'"
        @click="bottomPanel = bottomPanel === 'food' ? null : 'food'"
      >
        🍜 美食
      </button>
      <button
        class="flex flex-1 items-center justify-center gap-1.5 py-3 text-xs font-medium transition-colors"
        :class="bottomPanel === 'accommodation' ? 'bg-sky-50 text-sky-600' : 'text-stone-500 hover:bg-stone-50'"
        @click="bottomPanel = bottomPanel === 'accommodation' ? null : 'accommodation'"
      >
        🏨 住宿
      </button>
    </div>

    <!-- Bottom Panel -->
    <div v-if="bottomPanel" class="max-h-[200px] overflow-y-auto border-t border-stone-100 bg-stone-50 px-5 py-3">
      <!-- 交通汇总 -->
      <div v-if="bottomPanel === 'transport'">
        <p v-if="tripPlan.transport_summary" class="mb-2 text-xs text-stone-600">{{ tripPlan.transport_summary }}</p>
        <div v-if="allTransport.length" class="space-y-2">
          <div v-for="(t, i) in allTransport" :key="i" class="flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-xs">
            <span>{{ transportEmoji(t.mode) }}</span>
            <span class="text-stone-600">{{ t.mode }}</span>
            <span v-if="t.from_place && t.to_place" class="text-stone-400">{{ t.from_place }} → {{ t.to_place }}</span>
            <span v-if="t.duration" class="text-stone-400">{{ t.duration }}</span>
            <span v-if="t.estimated_cost" class="ml-auto font-medium text-stone-600">¥{{ t.estimated_cost }}</span>
          </div>
        </div>
        <p v-else class="text-xs text-stone-400">暂无交通信息</p>
      </div>

      <!-- 美食汇总 -->
      <div v-if="bottomPanel === 'food'">
        <p v-if="tripPlan.food_summary" class="mb-2 text-xs text-stone-600">{{ tripPlan.food_summary }}</p>
        <div v-if="allMeals.length" class="space-y-2">
          <div v-for="(m, i) in allMeals" :key="i" class="flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-xs">
            <span>{{ mealEmoji(m.meal_type) }}</span>
            <span class="font-medium text-stone-700">{{ m.name }}</span>
            <span class="text-stone-400">{{ m.meal_type }}</span>
            <span v-if="m.estimated_cost" class="ml-auto text-stone-500">¥{{ m.estimated_cost }}</span>
          </div>
        </div>
        <p v-else class="text-xs text-stone-400">暂无美食信息</p>
      </div>

      <!-- 住宿汇总 -->
      <div v-if="bottomPanel === 'accommodation'">
        <p v-if="tripPlan.accommodation_summary" class="mb-2 text-xs text-stone-600">{{ tripPlan.accommodation_summary }}</p>
        <div v-if="allHotels.length" class="space-y-2">
          <div v-for="(h, i) in allHotels" :key="i" class="rounded-lg bg-white px-3 py-2 text-xs">
            <span class="font-medium text-stone-700">{{ h.name }}</span>
            <span v-if="h.level" class="ml-2 text-stone-400">{{ h.level }}</span>
            <span v-if="h.estimated_cost" class="ml-2 text-amber-600">¥{{ h.estimated_cost }}</span>
            <div v-if="h.location" class="mt-1 text-stone-400">📍 {{ h.location }}</div>
          </div>
        </div>
        <p v-else class="text-xs text-stone-400">暂无住宿信息</p>
      </div>
    </div>
  </div>
</template>
