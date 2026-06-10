<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/api/client'
import { getDeviceId } from '@/utils/device'

const emit = defineEmits<{ close: [] }>()

interface Preference {
  id: number
  category: string
  key: string
  value: string
  confidence: number
}

const prefs = ref<Preference[]>([])
const loading = ref(true)
const error = ref('')

// 新增表单
const showAdd = ref(false)
const newCategory = ref('diet')
const newKey = ref('')
const newValue = ref('')

// 按类别分组
const grouped = computed(() => {
  const map: Record<string, Preference[]> = {}
  for (const p of prefs.value) {
    if (!map[p.category]) map[p.category] = []
    map[p.category].push(p)
  }
  return map
})

const categoryNames: Record<string, string> = {
  diet: '🍴 饮食偏好',
  budget: '💰 预算偏好',
  accommodation: '🏨 住宿偏好',
  transport: '🚗 出行偏好',
  general: '📋 通用偏好',
}

function catName(cat: string) {
  return categoryNames[cat] ?? `📁 ${cat}`
}

async function fetchPrefs() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get(`/memory/${getDeviceId()}/preferences`)
    prefs.value = res.data.preferences ?? []
  } catch {
    error.value = '加载偏好失败'
  } finally {
    loading.value = false
  }
}

async function del(category: string, key: string) {
  try {
    await api.delete(`/memory/${getDeviceId()}/preferences`, {
      params: { category, key },
    })
    prefs.value = prefs.value.filter(p => !(p.category === category && p.key === key))
  } catch {
    error.value = '删除失败'
  }
}

async function add() {
  if (!newKey.value.trim() || !newValue.value.trim()) return
  try {
    await api.post(`/memory/${getDeviceId()}/preferences`, {
      category: newCategory.value,
      key: newKey.value.trim(),
      value: newValue.value.trim(),
    })
    showAdd.value = false
    newKey.value = ''
    newValue.value = ''
    await fetchPrefs()
  } catch {
    error.value = '添加失败'
  }
}

onMounted(fetchPrefs)
</script>

<template>
  <Teleport to="body">
    <!-- 遮罩 -->
    <div class="fixed inset-0 z-40 bg-black/20" @click="emit('close')" />

    <!-- 抽屉 -->
    <div class="fixed right-0 top-0 z-50 flex h-full w-80 flex-col bg-white shadow-xl dark:bg-[#212121]">
      <!-- Header -->
      <div class="flex items-center justify-between border-b px-5 py-4 dark:border-stone-700">
        <h3 class="text-base font-semibold text-stone-800 dark:text-stone-200">偏好设置</h3>
        <button class="rounded-lg p-1 text-stone-400 hover:bg-stone-100 dark:hover:bg-[#2f2f2f]" @click="emit('close')">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Error -->
      <div v-if="error" class="mx-4 mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-950 dark:text-red-300">
        {{ error }}
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto px-5 py-4">
        <div v-if="loading" class="flex items-center justify-center py-12 text-sm text-stone-400 dark:text-stone-500">
          加载中...
        </div>

        <div v-else-if="prefs.length === 0" class="py-12 text-center">
          <p class="text-3xl mb-2">📋</p>
          <p class="text-sm text-stone-400 dark:text-stone-500">暂无偏好记录</p>
          <p class="mt-1 text-xs text-stone-300 dark:text-stone-600">保存偏好后，AI 会按你的习惯推荐行程和美食</p>
        </div>

        <div v-else v-for="(items, cat) in grouped" :key="cat" class="mb-5">
          <h4 class="mb-2 text-xs font-semibold uppercase text-stone-400 dark:text-stone-500">{{ catName(cat) }}</h4>
          <div class="space-y-2">
            <div
              v-for="p in items"
              :key="p.id"
              class="flex items-center justify-between rounded-lg border border-stone-100 bg-stone-50 px-3 py-2.5 dark:border-stone-700 dark:bg-[#1a1a1a]"
            >
              <div class="min-w-0 flex-1">
                <div class="text-sm font-medium text-stone-700 dark:text-stone-200">{{ p.key }}</div>
                <div class="mt-0.5 text-xs text-stone-500 dark:text-stone-400">{{ p.value }}</div>
              </div>
              <button
                class="ml-2 shrink-0 rounded p-1 text-stone-300 hover:bg-red-50 hover:text-red-400 dark:text-stone-600 dark:hover:bg-red-950 dark:hover:text-red-300"
                @click="del(p.category, p.key)"
              >
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 添加按钮 -->
      <div class="border-t px-5 py-4 dark:border-stone-700">
        <button
          v-if="!showAdd"
          class="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-stone-200 py-2.5 text-sm text-stone-400 hover:border-stone-400 hover:text-stone-500 dark:border-stone-700 dark:text-stone-500 dark:hover:border-stone-500 dark:hover:text-stone-300"
          @click="showAdd = true"
        >
          + 添加偏好
        </button>

        <div v-else class="space-y-3">
          <select v-model="newCategory" class="w-full rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-sm dark:border-stone-600 dark:bg-[#1a1a1a] dark:text-stone-200">
            <option value="diet">饮食偏好</option>
            <option value="budget">预算偏好</option>
            <option value="accommodation">住宿偏好</option>
            <option value="transport">出行偏好</option>
            <option value="general">通用偏好</option>
          </select>
          <input
            v-model="newKey"
            placeholder="键（如：忌口）"
            class="w-full rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-sm dark:border-stone-600 dark:bg-[#1a1a1a] dark:text-stone-200 dark:placeholder:text-stone-500"
          />
          <input
            v-model="newValue"
            placeholder="值（如：不吃辣）"
            class="w-full rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-sm dark:border-stone-600 dark:bg-[#1a1a1a] dark:text-stone-200 dark:placeholder:text-stone-500"
          />
          <div class="flex gap-2">
            <button
              class="flex-1 rounded-lg bg-stone-100 py-2 text-sm text-stone-500 dark:bg-[#2f2f2f] dark:text-stone-400"
              @click="showAdd = false; newKey = ''; newValue = ''"
            >
              取消
            </button>
            <button
              class="flex-1 rounded-lg bg-stone-800 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-stone-200 dark:text-stone-800"
              :disabled="!newKey.trim() || !newValue.trim()"
              @click="add"
            >
              保存
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
