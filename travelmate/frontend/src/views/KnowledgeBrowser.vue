<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'

const props = defineProps<{ dark?: boolean; toggleDark?: () => void }>()
const router = useRouter()

interface KnowledgeItem {
  city: string
  file: string
  description: string
  spot_count: number
  food_count: number
  size_kb: number
  char_count: number
}

const items = ref<KnowledgeItem[]>([])
const total = ref(0)
const loading = ref(true)
const searchKeyword = ref('')
const selectedCategory = ref('')
const selectedCity = ref('')
const cityContent = ref('')
const loadingContent = ref(false)
const categories = ref<{ id: string; name: string; count: number }[]>([])

async function fetchKnowledge() {
  loading.value = true
  try {
    const params: Record<string, any> = { limit: 50 }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (selectedCategory.value) params.category = selectedCategory.value
    const res = await api.get('/knowledge-browse/list', { params })
    items.value = res.data.items ?? []
    total.value = res.data.total ?? 0
  } catch { /* ignore */ }
  loading.value = false
}

async function fetchCategories() {
  try {
    const res = await api.get('/knowledge-browse/categories')
    categories.value = res.data.categories ?? []
  } catch { /* ignore */ }
}

async function viewCity(city: string) {
  selectedCity.value = city
  loadingContent.value = true
  cityContent.value = ''
  try {
    const res = await api.get(`/knowledge-browse/${city}/content`)
    cityContent.value = res.data.content ?? ''
  } catch { cityContent.value = '加载失败' }
  loadingContent.value = false
}

function renderMd(text: string): string {
  return text
    .replace(/^### (.+)$/gm, '<h4 class="font-semibold mt-4 mb-1 text-stone-700 dark:text-stone-300">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 class="font-bold mt-6 mb-2 text-stone-800 dark:text-stone-200 text-lg">$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li class="text-sm text-stone-600 dark:text-stone-400 ml-4 mb-1">$1</li>')
    .replace(/\n\n/g, '<br/>')
}

onMounted(() => { fetchKnowledge(); fetchCategories() })
</script>

<template>
  <div class="min-h-screen" :class="props.dark ? 'bg-[#212121]' : 'bg-stone-50'">
    <!-- 顶部导航 -->
    <div class="sticky top-0 z-30 flex items-center gap-3 border-b px-5 py-3" :class="props.dark ? 'bg-[#212121] border-stone-700' : 'bg-white border-stone-200'">
      <button class="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 dark:hover:bg-[#2f2f2f]" @click="router.push('/')">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
      </button>
      <h1 class="text-lg font-semibold" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">📚 知识库浏览</h1>
      <span class="ml-auto text-xs" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">共 {{ total }} 个城市</span>
    </div>

    <div class="mx-auto max-w-3xl px-4 py-6">
      <!-- 搜索栏 + 分类筛选 -->
      <div class="mb-4 space-y-3">
        <input
          v-model="searchKeyword"
          @input="fetchKnowledge"
          placeholder="🔍 搜索城市/景点名称..."
          class="w-full rounded-xl border px-4 py-2.5 text-sm outline-none focus:border-stone-400"
          :class="props.dark ? 'border-stone-700 bg-[#2a2a2a] text-stone-200 placeholder:text-stone-500' : 'border-stone-200 bg-white text-stone-800 placeholder:text-stone-400'"
        />
        <!-- 分类标签 -->
        <div v-if="categories.length" class="flex flex-wrap gap-1.5">
          <button
            class="rounded-full border px-2.5 py-1 text-[11px] transition-colors"
            :class="!selectedCategory ? 'border-stone-800 bg-stone-800 text-white dark:border-stone-200 dark:bg-stone-200 dark:text-stone-800' : 'border-stone-200 text-stone-500 hover:border-stone-400 dark:border-stone-600 dark:text-stone-400'"
            @click="selectedCategory = ''; fetchKnowledge()"
          >全部</button>
          <button
            v-for="cat in categories" :key="cat.id"
            class="rounded-full border px-2.5 py-1 text-[11px] transition-colors"
            :class="selectedCategory === cat.id ? 'border-stone-800 bg-stone-800 text-white dark:border-stone-200 dark:bg-stone-200 dark:text-stone-800' : 'border-stone-200 text-stone-500 hover:border-stone-400 dark:border-stone-600 dark:text-stone-400'"
            @click="selectedCategory = cat.id; fetchKnowledge()"
          >{{ cat.name }} ({{ cat.count }})</button>
        </div>
      </div>

      <div v-if="loading" class="py-12 text-center text-sm text-stone-400">加载中...</div>

      <div v-else-if="items.length === 0" class="py-12 text-center">
        <p class="text-3xl mb-2">📭</p>
        <p class="text-sm text-stone-400">暂无知识库数据</p>
      </div>

      <!-- 城市列表 -->
      <div v-else class="space-y-3">
        <div
          v-for="item in items" :key="item.city"
          class="rounded-xl border p-4 transition-colors cursor-pointer hover:shadow-md"
          :class="[
            props.dark ? 'border-stone-700 bg-[#2a2a2a] hover:bg-[#333]' : 'border-stone-200 bg-white hover:bg-stone-50',
            selectedCity === item.city ? 'ring-2 ring-stone-400' : ''
          ]"
          @click="viewCity(item.city)"
        >
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-semibold text-lg" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">📍 {{ item.city }}</h3>
            <div class="flex items-center gap-2">
              <span v-if="item.category" class="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] dark:bg-stone-700 dark:text-stone-400">{{ item.category }}</span>
              <span class="text-xs" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">{{ item.size_kb }} KB</span>
            </div>
          </div>
          <p class="text-xs mb-2 line-clamp-2" :class="props.dark ? 'text-stone-400' : 'text-stone-500'">{{ item.description }}</p>
          <div class="flex gap-3 text-xs" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">
            <span>🏛️ {{ item.spot_count }}个景点</span>
            <span>🍜 {{ item.food_count }}道美食</span>
            <span>📄 {{ item.char_count }}字</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 城市详情弹窗 -->
    <Teleport to="body">
      <div v-if="selectedCity" class="fixed inset-0 z-50 flex items-end sm:items-center justify-center" @click.self="selectedCity = ''">
        <div class="w-full sm:w-[600px] max-h-[80vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl bg-white shadow-2xl dark:bg-[#2a2a2a] dark:border dark:border-stone-700">
          <div class="sticky top-0 flex items-center justify-between border-b px-5 py-3 bg-white dark:bg-[#2a2a2a] dark:border-stone-700 rounded-t-2xl z-10">
            <h3 class="font-semibold" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">📍 {{ selectedCity }}</h3>
            <button class="text-stone-400 hover:text-stone-600 text-lg" @click="selectedCity = ''">✕</button>
          </div>
          <div class="p-5">
            <div v-if="loadingContent" class="py-8 text-center text-sm text-stone-400">加载中...</div>
            <div v-else class="prose prose-sm max-w-none" :class="props.dark ? 'prose-invert' : ''" v-html="renderMd(cityContent)" />
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
