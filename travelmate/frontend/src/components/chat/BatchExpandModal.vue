<script setup lang="ts">
import { ref } from 'vue'
import { getDeviceId } from '@/utils/device'

const emit = defineEmits<{ close: [] }>()

const inputText = ref('')
const isRunning = ref(false)
const fetchError = ref('')
const progress = ref<{ spot: string; index: number; total: number; status: string; chunks?: number; cached?: boolean; error?: string }[]>([])
const completeResult = ref<{ total: number; success: number; failed: number } | null>(null)

const API_BASE = 'http://localhost:8000'

const CATEGORIES = ['景点', '非遗文化', '美食', '民俗', '历史遗址', '名山大川', '古城古镇', '博物馆'] as const
const selectedCategory = ref<string>('景点')
const generatingPresets = ref(false)

const CATEGORY_PLACEHOLDERS: Record<string, string> = {
  '景点': '西湖，九寨沟，张家界',
  '非遗文化': '京剧，皮影戏，景德镇陶瓷',
  '美食': '广州早茶，成都火锅，北京烤鸭',
  '民俗': '苗族银饰，藏族唐卡，春节庙会',
  '历史遗址': '莫高窟，三星堆，殷墟',
  '名山大川': '黄山，泰山，长白山',
  '古城古镇': '平遥古城，乌镇，凤凰古城',
  '博物馆': '故宫博物院，国家博物馆，敦煌研究院',
}

function parseSpots(): string[] {
  return inputText.value
    .split(/[,，\n\r]+/)
    .map(s => s.trim())
    .filter(s => s.length >= 2)
}

async function usePresets() {
  if (generatingPresets.value) return
  generatingPresets.value = true
  try {
    const res = await fetch(`${API_BASE}/knowledge/generate-presets?category=${encodeURIComponent(selectedCategory.value)}&count=15`)
    const data = await res.json()
    if (data.items?.length) {
      inputText.value = data.items.join('，')
    }
  } catch {
    // 静默失败
  } finally {
    generatingPresets.value = false
  }
}

async function startBatchExpand() {
  const spots = parseSpots()
  if (spots.length === 0 || isRunning.value) return

  isRunning.value = true
  fetchError.value = ''
  progress.value = []
  completeResult.value = null

  try {
    const res = await fetch(`${API_BASE}/knowledge/auto-expand-batch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Device-ID': getDeviceId(),
      },
      body: JSON.stringify({ spot_names: spots }),
    })

    if (!res.ok) {
      const errText = await res.text().catch(() => res.statusText)
      throw new Error(`服务器返回 ${res.status}: ${errText}`)
    }

    const reader = res.body?.getReader()
    if (!reader) throw new Error('无法读取响应流')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.type === 'progress') {
            progress.value.push({ spot: data.spot, index: data.index, total: data.total, status: data.status })
          } else if (data.type === 'done') {
            const last = progress.value.find(p => p.spot === data.spot && p.index === data.index)
            if (last) {
              last.status = 'done'
              last.chunks = data.chunks
              last.cached = data.cached
            }
          } else if (data.type === 'error') {
            const last = progress.value.find(p => p.spot === data.spot && p.index === data.index)
            if (last) {
              last.status = 'error'
              last.error = data.message
            }
          } else if (data.type === 'complete') {
            completeResult.value = { total: data.total, success: data.success, failed: data.failed }
          }
        } catch { /* 忽略解析错误 */ }
      }
    }
  } catch (err: any) {
    fetchError.value = err.message || '连接失败，请检查后端是否启动'
    progress.value.push({ spot: '连接失败', index: 0, total: 0, status: 'error', error: err.message })
  } finally {
    isRunning.value = false
  }
}

function statusIcon(s: string) {
  if (s === 'generating') return '⏳'
  if (s === 'done') return '✅'
  if (s === 'error') return '❌'
  return '⏳'
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30" @click.self="emit('close')">
      <div class="w-full max-w-lg rounded-2xl bg-white shadow-2xl dark:bg-stone-800 dark:border dark:border-stone-700">
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-stone-200 px-5 py-4 dark:border-stone-700">
          <div>
            <h3 class="text-base font-semibold text-stone-800 dark:text-stone-100">批量扩充知识库</h3>
            <p class="mt-0.5 text-xs text-stone-400 dark:text-stone-500">输入名称，AI 自动生成知识文档并入库</p>
          </div>
          <button class="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-700" @click="emit('close')">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <!-- Body -->
        <div class="px-5 py-4">
          <!-- 输入区（未运行且未完成时显示） -->
          <div v-if="!isRunning && !completeResult">
            <textarea
              v-model="inputText"
              rows="4"
              :placeholder="`输入名称，用逗号或换行分隔，例如：\n${CATEGORY_PLACEHOLDERS[selectedCategory]}`"
              class="w-full resize-none rounded-xl border border-stone-200 bg-stone-50 px-3 py-2.5 text-sm text-stone-800 outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 dark:border-stone-600 dark:bg-stone-700 dark:text-stone-100"
            />
            <div class="mt-2 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <select
                  v-model="selectedCategory"
                  class="rounded-lg border border-stone-200 bg-stone-50 px-2 py-1 text-xs text-stone-600 outline-none dark:border-stone-600 dark:bg-stone-700 dark:text-stone-300"
                >
                  <option v-for="cat in CATEGORIES" :key="cat" :value="cat">{{ cat }}</option>
                </select>
                <button
                  class="text-xs text-stone-400 hover:text-amber-500 transition-colors disabled:opacity-50"
                  :disabled="generatingPresets"
                  @click="usePresets"
                >
                  {{ generatingPresets ? '生成中...' : `使用预设（随机15个${selectedCategory}）` }}
                </button>
              </div>
              <span class="text-xs text-stone-400">{{ parseSpots().length }} 个项目</span>
            </div>
          </div>

          <!-- 进度区（运行中/完成时显示） -->
          <div v-else class="max-h-72 overflow-y-auto">
            <!-- 连接错误横幅 -->
            <div v-if="fetchError" class="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
              {{ fetchError }}
            </div>

            <div
              v-for="(p, i) in progress"
              :key="i"
              class="flex items-center gap-2 border-b border-stone-100 py-2 dark:border-stone-700"
            >
              <span class="shrink-0 text-sm">{{ statusIcon(p.status) }}</span>
              <span class="min-w-0 flex-1 truncate text-sm text-stone-700 dark:text-stone-200">{{ p.spot }}</span>
              <span
                v-if="p.status === 'done'"
                class="shrink-0 text-xs text-emerald-500"
              >
                {{ p.cached ? '已缓存' : `+${p.chunks} 段落` }}
              </span>
              <span v-else-if="p.status === 'error'" class="shrink-0 text-xs text-red-400 truncate max-w-[140px]" :title="p.error">
                {{ p.error }}
              </span>
              <span v-else class="shrink-0 text-xs text-amber-500 animate-pulse">生成中...</span>
            </div>

            <!-- 完成汇总 -->
            <div v-if="completeResult" class="mt-3 rounded-lg bg-stone-50 px-3 py-2.5 text-sm dark:bg-stone-700">
              <span class="font-medium text-stone-700 dark:text-stone-200">完成</span>
              <span class="ml-2 text-emerald-500">{{ completeResult.success }} 成功</span>
              <span v-if="completeResult.failed > 0" class="ml-2 text-red-400">{{ completeResult.failed }} 失败</span>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-2 border-t border-stone-200 px-5 py-3 dark:border-stone-700">
          <button
            v-if="!isRunning"
            class="rounded-lg border border-stone-200 px-4 py-2 text-sm text-stone-600 hover:bg-stone-50 dark:border-stone-600 dark:text-stone-300 dark:hover:bg-stone-700"
            @click="emit('close')"
          >
            {{ completeResult ? '关闭' : '取消' }}
          </button>
          <button
            v-if="!isRunning && !completeResult"
            class="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="parseSpots().length === 0"
            @click="startBatchExpand"
          >
            开始扩充（{{ parseSpots().length }} 个）
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
