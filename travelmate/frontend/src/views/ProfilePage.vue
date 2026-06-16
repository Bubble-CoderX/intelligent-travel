<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { getDeviceId } from '@/utils/device'

const props = defineProps<{ dark?: boolean; toggleDark?: () => void }>()
const router = useRouter()

interface PrefItem {
  id: number
  category: string
  key: string
  value: string
  confidence: number
  source: string
  updated_at: string
}

const prefs = ref<PrefItem[]>([])
const loading = ref(true)
const stats = ref({ total: 0, conversation_based: 0, manual_based: 0, last_updated: '' })

const LABEL_MAP: Record<string, string> = {
  group_size: '出行人数', composition: '人员构成', child_age: '儿童年龄',
  elder_count: '老人数量', travel_style: '旅行风格', interests: '兴趣标签',
  taste_preference: '口味偏好', fitness_level: '体力水平', photo_need: '拍照需求',
  dietary: '饮食忌口', accommodation: '住宿偏好', atmosphere: '氛围偏好',
  budget_daily: '日均预算', budget_tier: '预算等级', allergies: '过敏史',
  special_needs: '特殊需求', transport_preference: '出行方式',
  departure_city: '出发地', current_city: '当前城市',
}

const COMPOSITION_MAP: Record<string, string> = {
  solo: '独自出行', couple: '情侣出行',
  family_baby: '家庭（带婴儿）', family_child: '家庭（带小孩）',
  family_elder: '家庭（带老人）', family_child_elder: '家庭（带小孩+老人）',
  group: '多人结伴',
}
const STYLE_MAP: Record<string, string> = {
  deep: '深度游', checkin: '打卡游', leisure: '休闲游', adventure: '探险游',
}
const INTEREST_MAP: Record<string, string> = {
  history: '历史', food: '美食', shopping: '购物', nature: '自然',
  art: '艺术', photography: '拍照', kid_friendly: '亲子',
}
const TASTE_MAP: Record<string, string> = {
  '不吃辣': '不吃辣', '不吃酸': '不吃酸', '不吃甜': '不吃甜',
  '不吃咸': '不吃咸', '不吃油腻': '不吃油腻',
  '清淡': '清淡', '重口味': '重口味',
}
const BUDGET_TIER_MAP: Record<string, string> = {
  poor: '穷游', economic: '经济', comfortable: '舒适', luxury: '奢华',
}

// 出行档案固定字段定义
interface ProfileFieldDef {
  key: string
  label: string
  type: 'text' | 'list' | 'map'
  map?: Record<string, string>
  alwaysShow: boolean
  dependsOn?: string
}
const PROFILE_FIELDS: ProfileFieldDef[] = [
  { key: 'group_size', label: '出行人数', type: 'text', alwaysShow: true },
  { key: 'composition', label: '人员构成', type: 'map', map: COMPOSITION_MAP, alwaysShow: true },
  { key: 'child_age', label: '儿童年龄', type: 'text', alwaysShow: false, dependsOn: 'composition' },
  { key: 'elder_count', label: '老人数量', type: 'text', alwaysShow: false, dependsOn: 'composition' },
  { key: 'travel_style', label: '旅行风格', type: 'map', map: STYLE_MAP, alwaysShow: true },
  { key: 'interests', label: '兴趣标签', type: 'list', alwaysShow: true },
  { key: 'taste_preference', label: '口味偏好', type: 'list', alwaysShow: true },
  { key: 'accommodation', label: '住宿偏好', type: 'text', alwaysShow: true },
  { key: 'budget_tier', label: '预算等级', type: 'map', map: BUDGET_TIER_MAP, alwaysShow: true },
]

function getProfileItem(key: string): PrefItem | undefined {
  return prefs.value.find(p => p.category === 'travel_profile' && p.key === key)
}
function shouldShowField(field: ProfileFieldDef): boolean {
  if (field.alwaysShow) return true
  if (field.dependsOn) {
    const dep = getProfileItem(field.dependsOn)
    if (!dep) return false
    if (field.key === 'child_age') return dep.value.includes('child') || dep.value.includes('baby')
    if (field.key === 'elder_count') return dep.value.includes('elder')
  }
  return !!getProfileItem(field.key)
}

function displayValue(item: PrefItem): string {
  const val = item.value
  if (item.key === 'composition') return COMPOSITION_MAP[val] || val
  if (item.key === 'travel_style') return STYLE_MAP[val] || val
  if (item.key === 'budget_tier') return BUDGET_TIER_MAP[val] || val
  if (item.key === 'budget_daily') return `${val} 元/人/天`
  // 住宿偏好可能是单值或JSON列表
  if (item.key === 'accommodation' && val.startsWith('[')) {
    try {
      const arr = JSON.parse(val)
      if (Array.isArray(arr)) return arr.join('、')
    } catch { /* ignore */ }
  }
  // 列表型
  if (val.startsWith('[')) {
    try {
      const arr = JSON.parse(val)
      if (Array.isArray(arr)) {
        const map = item.key === 'taste_preference' ? TASTE_MAP : INTEREST_MAP
        return arr.map(v => map[v] ?? v).join('、')
      }
    } catch { /* ignore */ }
  }
  return val
}

async function fetchPrefs() {
  loading.value = true
  try {
    const res = await api.get(`/memory/${getDeviceId()}/preferences`)
    prefs.value = res.data.preferences ?? []
    stats.value = {
      total: prefs.value.length,
      conversation_based: prefs.value.filter(p => p.source === 'conversation').length,
      manual_based: prefs.value.filter(p => p.source !== 'conversation').length,
      last_updated: prefs.value[0]?.updated_at || '',
    }
  } catch { /* ignore */ }
  loading.value = false
}

onMounted(fetchPrefs)
</script>

<template>
  <div class="min-h-screen" :class="props.dark ? 'bg-[#212121]' : 'bg-stone-50'">
    <!-- 顶部导航 -->
    <div class="sticky top-0 z-30 flex items-center gap-3 border-b px-5 py-3" :class="props.dark ? 'bg-[#212121] border-stone-700' : 'bg-white border-stone-200'">
      <button class="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 dark:hover:bg-[#2f2f2f]" @click="router.push('/')">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
      </button>
      <h1 class="text-lg font-semibold" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">👤 我的档案</h1>
    </div>

    <div class="mx-auto max-w-3xl px-4 py-6">
      <div v-if="loading" class="py-12 text-center text-sm text-stone-400">加载中...</div>

      <div v-else-if="prefs.length === 0" class="py-12 text-center">
        <p class="text-3xl mb-2">📋</p>
        <p class="text-sm text-stone-400">暂无偏好记录</p>
        <p class="mt-1 text-xs text-stone-300 dark:text-stone-600">跟AI聊几句就能自动提取你的旅行档案</p>
      </div>

      <div v-else class="space-y-6">
        <!-- 出行档案（固定字段，始终显示） -->
        <div>
          <h3 class="mb-3 text-sm font-semibold" :class="props.dark ? 'text-stone-300' : 'text-stone-600'">👤 出行档案 <span class="font-normal text-stone-400">（对话自动提取）</span></h3>
          <div class="space-y-1.5">
            <div v-for="field in PROFILE_FIELDS" :key="field.key"
              v-show="shouldShowField(field)"
              class="flex items-center justify-between rounded-lg border px-3 py-2.5"
              :class="props.dark ? 'border-stone-700 bg-[#2a2a2a]' : 'border-stone-100 bg-white'"
            >
              <div>
                <div class="text-xs" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">{{ field.label }}</div>
                <div class="mt-0.5 text-sm font-medium"
                  :class="getProfileItem(field.key) ? (props.dark ? 'text-stone-200' : 'text-stone-700') : (props.dark ? 'text-stone-600' : 'text-stone-300')"
                >
                  {{ getProfileItem(field.key) ? displayValue(getProfileItem(field.key)!) : '未设置' }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 精确设置 -->
        <div>
          <h3 class="mb-3 text-sm font-semibold" :class="props.dark ? 'text-stone-300' : 'text-stone-600'">✏️ 精确设置 <span class="font-normal text-stone-400">（手动设置，可编辑）</span></h3>
          <div class="space-y-1.5">
            <div v-for="key in ['budget_daily', 'budget_tier', 'allergies', 'special_needs', 'transport_preference']" :key="key"
              class="flex items-center justify-between rounded-lg border px-3 py-2.5"
              :class="props.dark ? 'border-stone-700 bg-[#2a2a2a]' : 'border-stone-100 bg-white'"
            >
              <div>
                <div class="text-xs" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">{{ LABEL_MAP[key] ?? key }}</div>
                <div class="mt-0.5 text-sm font-medium" :class="props.dark ? 'text-stone-200' : 'text-stone-700'">
                  {{ (() => { const found = prefs.find(x => x.key === key); return found ? displayValue(found) : '未设置' })() }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 系统信息 -->
        <div>
          <h3 class="mb-3 text-sm font-semibold" :class="props.dark ? 'text-stone-300' : 'text-stone-600'">📍 系统信息 <span class="font-normal text-stone-400">（自动定位，不可编辑）</span></h3>
          <div class="space-y-1.5">
            <div v-for="key in ['departure_city', 'current_city']" :key="key"
              class="flex items-center justify-between rounded-lg border px-3 py-2.5"
              :class="props.dark ? 'border-stone-700 bg-[#2a2a2a]' : 'border-stone-100 bg-white'"
            >
              <div>
                <div class="text-xs" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">{{ LABEL_MAP[key] ?? key }}</div>
                <div class="mt-0.5 text-sm font-medium" :class="props.dark ? 'text-stone-200' : 'text-stone-700'">
                  {{ (() => { const found = prefs.find(x => x.key === key); return found ? found.value : '未获取' })() }}
                </div>
              </div>
              <span class="text-[10px]" :class="props.dark ? 'text-stone-600' : 'text-stone-300'">自动获取</span>
            </div>
          </div>
        </div>

        <!-- 统计 -->
        <div class="rounded-xl border p-4" :class="props.dark ? 'border-stone-700 bg-[#2a2a2a]' : 'border-stone-100 bg-white'">
          <div class="flex items-center gap-4 text-xs" :class="props.dark ? 'text-stone-400' : 'text-stone-500'">
            <span>📊 已记录 {{ stats.total }} 项</span>
            <span>💬 对话提取 {{ stats.conversation_based }} 项</span>
            <span>✏️ 手动设置 {{ stats.manual_based }} 项</span>
          </div>
          <div v-if="stats.last_updated" class="mt-2 text-xs" :class="props.dark ? 'text-stone-600' : 'text-stone-300'">
            最近更新 {{ stats.last_updated }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
