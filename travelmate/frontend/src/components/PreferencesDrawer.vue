<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/api/client'
import { getDeviceId } from '@/utils/device'

const emit = defineEmits<{ close: [] }>()

// ── 数据 ──────────────────────────────────────────
interface PrefItem {
  id: number
  category: string
  key: string
  value: string
  confidence: number
}

const allPrefs = ref<PrefItem[]>([])
const loading = ref(true)
const error = ref('')

// 出行档案（travel_profile）
const profileLabels: Record<string, { label: string; type: string }> = {
  group_size:        { label: '出行人数', type: 'text' },
  composition:       { label: '人员构成', type: 'text' },
  child_age:         { label: '儿童年龄', type: 'text' },
  elder_count:       { label: '老人数量', type: 'text' },
  travel_style:      { label: '旅行风格', type: 'text' },
  interests:         { label: '兴趣标签', type: 'list' },
  taste_preference:  { label: '口味偏好', type: 'list' },
  dietary:           { label: '饮食忌口', type: 'list' },
  accommodation:     { label: '住宿偏好', type: 'text' },
  fitness_level:     { label: '体力水平', type: 'text' },
  photo_need:        { label: '拍照需求', type: 'text' },
  atmosphere:        { label: '氛围偏好', type: 'text' },
  allergies:         { label: '过敏史', type: 'list' },
  special_needs:     { label: '特殊需求', type: 'list' },
  budget_daily:      { label: '日均预算', type: 'text' },
  budget_tier:       { label: '预算等级', type: 'text' },
  transport_preference: { label: '出行方式', type: 'text' },
}

// 出行档案固定字段定义（始终显示，无值时显示"未设置"）
interface ProfileFieldDef {
  key: string
  label: string
  type: 'text' | 'list' | 'map' | 'budget'
  map?: Record<string, string>
  /** 是否始终显示（false = 仅在有值时显示） */
  alwaysShow: boolean
  /** 依赖字段：仅当依赖字段有值时才显示 */
  dependsOn?: string
}

const PROFILE_FIELDS: ProfileFieldDef[] = [
  // 区域一：基本信息
  { key: 'group_size', label: '出行人数', type: 'text', alwaysShow: true },
  { key: 'composition', label: '人员构成', type: 'map', map: {} as Record<string, string>, alwaysShow: true },
  { key: 'child_count', label: '小孩数量', type: 'text', alwaysShow: false, dependsOn: 'composition' },
  { key: 'child_age', label: '儿童年龄', type: 'text', alwaysShow: false, dependsOn: 'composition' },
  { key: 'elder_count', label: '老人数量', type: 'text', alwaysShow: false, dependsOn: 'composition' },
  // 区域二：偏好信息
  { key: 'travel_style', label: '旅行风格', type: 'map', map: {} as Record<string, string>, alwaysShow: true },
  { key: 'interests', label: '兴趣标签', type: 'list', alwaysShow: true },
  { key: 'taste_preference', label: '口味偏好', type: 'list', alwaysShow: true },
  { key: 'dietary', label: '饮食忌口', type: 'list', alwaysShow: true },
  { key: 'accommodation', label: '住宿偏好', type: 'text', alwaysShow: true },
  { key: 'budget_tier', label: '预算等级', type: 'map', map: {} as Record<string, string>, alwaysShow: true },
  // 区域三：健康信息
  { key: 'special_needs', label: '特殊需求', type: 'list', alwaysShow: true },
]

const compositionMap: Record<string, string> = {
  solo: '独自出行', couple: '情侣出行',
  family_baby: '家庭（带婴儿）', family_child: '家庭（带小孩）',
  family_elder: '家庭（带老人）', family_child_elder: '家庭（带小孩+老人）',
  group: '多人结伴',
}
const styleMap: Record<string, string> = {
  deep: '深度游', checkin: '打卡游', leisure: '休闲游', adventure: '探险游',
}
const transportMap: Record<string, string> = {
  drive: '偏好自驾', public: '偏好公共交通', flexible: '灵活推荐',
}
const interestMap: Record<string, string> = {
  history: '历史', food: '美食', shopping: '购物', nature: '自然',
  art: '艺术', photography: '拍照', kid_friendly: '亲子',
}
const tasteMap: Record<string, string> = {
  '不吃辣': '不吃辣', '不吃酸': '不吃酸', '不吃甜': '不吃甜',
  '不吃咸': '不吃咸', '不吃油腻': '不吃油腻',
  '清淡': '清淡', '重口味': '重口味',
}
const budgetTierMap: Record<string, string> = {
  poor: '穷游', economic: '经济', comfortable: '舒适', luxury: '奢华',
}

// 精确设置区
const showEdit = ref<'budget' | 'allergies' | 'special_needs' | 'transport' | null>(null)
const editBudget = ref('')
const editAllergies = ref('')
const editSpecialNeeds = ref('')
const editTransport = ref('flexible')

// 系统信息
const systemPrefs = computed(() =>
  allPrefs.value.filter(p => p.key === 'departure_city' || p.key === 'current_city')
)

// 出行档案 — 基于固定字段定义，始终显示关键字段
const profilePrefs = computed(() =>
  allPrefs.value.filter(p => p.category === 'travel_profile' && !['departure_city', 'current_city'].includes(p.key))
)

// 获取某个 profile 字段的 PrefItem（可能不存在）
function getProfileItem(key: string): PrefItem | undefined {
  return allPrefs.value.find(p => p.category === 'travel_profile' && p.key === key)
}

// 判断固定字段是否应该显示
function shouldShowField(field: ProfileFieldDef): boolean {
  if (field.alwaysShow) return true
  // dependsOn：仅当依赖字段有值时显示
  if (field.dependsOn) {
    const dep = getProfileItem(field.dependsOn)
    if (!dep) return false
    // composition 有值且包含 child/elder/baby 关键字时才显示子字段
    if (field.key === 'child_age' || field.key === 'child_count' || field.key === 'elder_count') {
      const comp = dep.value
      if (field.key === 'child_age' || field.key === 'child_count') return comp.includes('child') || comp.includes('baby')
      if (field.key === 'elder_count') return comp.includes('elder')
    }
  }
  return !!getProfileItem(field.key)
}

// 已设置的精确设置
function getProfileVal(key: string): string {
  const p = allPrefs.value.find(x => x.category === 'travel_profile' && x.key === key)
  return p?.value ?? ''
}

function displayValue(item: PrefItem): string {
  const info = profileLabels[item.key]
  if (!info) return item.value

  // 列表型
  if (info.type === 'list') {
    try {
      const arr = JSON.parse(item.value)
      if (Array.isArray(arr)) {
        const map = item.key === 'taste_preference' ? tasteMap : interestMap
        return arr.map(v => map[v] ?? v).join('、')
      }
    } catch { /* ignore */ }
    return item.value
  }
  // 枚举映射
  if (item.key === 'composition') return compositionMap[item.value] ?? item.value
  if (item.key === 'travel_style') return styleMap[item.value] ?? item.value
  if (item.key === 'transport_preference') return transportMap[item.value] ?? item.value
  if (item.key === 'budget_tier') return budgetTierMap[item.value] ?? item.value
  if (item.key === 'budget_daily') return `${item.value} 元/人/天`
  // 住宿偏好可能是单值或JSON列表
  if (item.key === 'accommodation' && item.value.startsWith('[')) {
    try {
      const arr = JSON.parse(item.value)
      if (Array.isArray(arr)) return arr.join('、')
    } catch { /* ignore */ }
  }
  return item.value
  return item.value
}

// ── 加载 ──────────────────────────────────────────
async function fetchPrefs() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get(`/memory/${getDeviceId()}/preferences`)
    allPrefs.value = res.data.preferences ?? []
  } catch {
    error.value = '加载偏好失败'
  } finally {
    loading.value = false
  }
}

// ── 删除单条偏好 ──────────────────────────────────
async function delPref(category: string, key: string) {
  try {
    await api.delete(`/memory/${getDeviceId()}/preferences`, { params: { category, key } })
    allPrefs.value = allPrefs.value.filter(p => !(p.category === category && p.key === key))
  } catch {
    error.value = '删除失败'
  }
}

// ── 精确设置保存 ──────────────────────────────────
async function savePref(category: string, key: string, value: string) {
  try {
    await api.post(`/memory/${getDeviceId()}/preferences`, { category, key, value })
    // 更新本地数据
    const existing = allPrefs.value.find(p => p.category === category && p.key === key)
    if (existing) {
      existing.value = value
    } else {
      allPrefs.value.push({ id: Date.now(), category, key, value, confidence: 1.0 })
    }
    showEdit.value = null
  } catch {
    error.value = '保存失败'
  }
}

function startEditBudget() {
  editBudget.value = getProfileVal('budget_daily') || ''
  showEdit.value = 'budget'
}
function startEditAllergies() {
  const raw = getProfileVal('allergies')
  try { editAllergies.value = JSON.parse(raw).join('、') } catch { editAllergies.value = raw }
  showEdit.value = 'allergies'
}
function startEditSpecialNeeds() {
  const raw = getProfileVal('special_needs')
  try { editSpecialNeeds.value = JSON.parse(raw).join('、') } catch { editSpecialNeeds.value = raw }
  showEdit.value = 'special_needs'
}
function startEditTransport() {
  editTransport.value = getProfileVal('transport_preference') || 'flexible'
  showEdit.value = 'transport'
}

function saveBudget() {
  const num = parseInt(editBudget.value)
  if (!isNaN(num) && num > 0) {
    savePref('travel_profile', 'budget_daily', String(num))
    // 同步计算 tier
    if (num <= 200) savePref('travel_profile', 'budget_tier', 'poor')
    else if (num <= 500) savePref('travel_profile', 'budget_tier', 'economic')
    else if (num <= 1000) savePref('travel_profile', 'budget_tier', 'comfortable')
    else savePref('travel_profile', 'budget_tier', 'luxury')
  }
}
function saveAllergies() {
  const arr = editAllergies.value.split(/[、,，\s]+/).filter(s => s.trim())
  savePref('travel_profile', 'allergies', JSON.stringify(arr))
}
function saveSpecialNeeds() {
  const arr = editSpecialNeeds.value.split(/[、,，\s]+/).filter(s => s.trim())
  savePref('travel_profile', 'special_needs', JSON.stringify(arr))
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

        <div v-else-if="allPrefs.length === 0" class="py-12 text-center">
          <p class="text-3xl mb-2">📋</p>
          <p class="text-sm text-stone-400 dark:text-stone-500">暂无偏好记录</p>
          <p class="mt-1 text-xs text-stone-300 dark:text-stone-600">跟AI聊几句就能自动提取你的旅行档案</p>
        </div>

        <div v-else class="space-y-6">
          <!-- ═══ 区域一：出行档案（固定字段，始终显示）═══ -->
          <div>
            <h4 class="mb-3 text-xs font-semibold uppercase text-stone-400 dark:text-stone-500">👤 出行档案</h4>
            <p class="mb-2 text-[11px] text-stone-300 dark:text-stone-600">在对话中自然表达即可自动提取</p>
            <div class="space-y-1.5">
              <div
                v-for="field in PROFILE_FIELDS"
                :key="field.key"
                v-show="shouldShowField(field)"
                class="flex items-center justify-between rounded-lg border border-stone-100 bg-stone-50 px-3 py-2 dark:border-stone-700 dark:bg-[#1a1a1a]"
              >
                <div class="min-w-0 flex-1">
                  <div class="text-xs text-stone-400 dark:text-stone-500">{{ field.label }}</div>
                  <div class="mt-0.5 text-sm font-medium"
                    :class="getProfileItem(field.key) ? 'text-stone-700 dark:text-stone-200' : 'text-stone-300 dark:text-stone-600'"
                  >
                    {{ getProfileItem(field.key) ? displayValue(getProfileItem(field.key)!) : '未设置' }}
                  </div>
                </div>
                <button
                  v-if="getProfileItem(field.key)"
                  class="ml-2 shrink-0 rounded p-1 text-stone-300 hover:bg-red-50 hover:text-red-400 dark:text-stone-600 dark:hover:bg-red-950 dark:hover:text-red-300"
                  @click="delPref('travel_profile', field.key)"
                  title="删除"
                >
                  <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- ═══ 区域二：精确设置 ═══ -->
          <div>
            <h4 class="mb-3 text-xs font-semibold uppercase text-stone-400 dark:text-stone-500">⚙️ 精确设置</h4>
            <p class="mb-2 text-[11px] text-stone-300 dark:text-stone-600">以下信息需要手动设置，精度更高</p>
            <div class="space-y-1.5">
              <!-- 日均预算 -->
              <div class="rounded-lg border border-stone-100 bg-stone-50 px-3 py-2.5 dark:border-stone-700 dark:bg-[#1a1a1a]">
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-xs text-stone-400 dark:text-stone-500">💰 日均预算</div>
                    <div class="mt-0.5 text-sm font-medium text-stone-700 dark:text-stone-200">
                      {{ getProfileVal('budget_daily') ? `${getProfileVal('budget_daily')} 元/人/天` : '未设置' }}
                    </div>
                  </div>
                  <button class="text-xs font-medium" :class="showEdit === 'budget' ? 'text-red-500 hover:text-red-700' : 'text-stone-400 hover:text-stone-600 dark:hover:text-stone-200'" @click="showEdit === 'budget' ? showEdit = null : startEditBudget()">{{ showEdit === 'budget' ? '关闭' : '编辑' }}</button>
                </div>
                <div v-if="showEdit === 'budget'" class="mt-2 flex gap-2">
                  <input v-model="editBudget" type="number" placeholder="如 500" class="flex-1 rounded-lg border border-stone-200 bg-white px-2.5 py-1.5 text-sm outline-none focus:border-stone-400 dark:border-stone-600 dark:bg-[#2a2a2a] dark:text-stone-200" />
                  <button class="rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-40 dark:disabled:opacity-40" :class="editBudget.trim() ? 'bg-stone-800 text-white dark:bg-stone-200 dark:text-stone-800' : 'bg-stone-300 text-stone-500 cursor-not-allowed dark:bg-stone-600 dark:text-stone-400'" :disabled="!editBudget.trim()" @click="saveBudget">保存</button>
                </div>
              </div>

              <!-- 过敏史 -->
              <div class="rounded-lg border border-stone-100 bg-stone-50 px-3 py-2.5 dark:border-stone-700 dark:bg-[#1a1a1a]">
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-xs text-stone-400 dark:text-stone-500">🤧 过敏史</div>
                    <div class="mt-0.5 text-sm font-medium text-stone-700 dark:text-stone-200">
                      {{ (() => { const raw = getProfileVal('allergies'); if (!raw) return '未设置'; try { return JSON.parse(raw).join('、') } catch { return raw } })() }}
                    </div>
                  </div>
                  <button class="text-xs font-medium" :class="showEdit === 'allergies' ? 'text-red-500 hover:text-red-700' : 'text-stone-400 hover:text-stone-600 dark:hover:text-stone-200'" @click="showEdit === 'allergies' ? showEdit = null : startEditAllergies()">{{ showEdit === 'allergies' ? '关闭' : '编辑' }}</button>
                </div>
                <div v-if="showEdit === 'allergies'" class="mt-2">
                  <input v-model="editAllergies" placeholder="用顿号分隔，如：花粉过敏、鼻炎" class="w-full rounded-lg border border-stone-200 bg-white px-2.5 py-1.5 text-sm outline-none focus:border-stone-400 dark:border-stone-600 dark:bg-[#2a2a2a] dark:text-stone-200" />
                  <div class="mt-1.5 flex flex-wrap gap-1">
                    <button v-for="opt in ['花粉过敏','季节性鼻炎','尘螨过敏','宠物毛发过敏','紫外线过敏','金属过敏']" :key="opt"
                      class="rounded-full border border-stone-200 bg-white px-2 py-0.5 text-[10px] text-stone-500 hover:border-stone-400 dark:border-stone-600 dark:bg-[#2a2a2a] dark:text-stone-400"
                      @click="editAllergies = editAllergies ? editAllergies + '、' + opt : opt"
                    >{{ opt }}</button>
                  </div>
                  <button class="mt-2 rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-40 dark:disabled:opacity-40" :class="editAllergies.trim() ? 'bg-stone-800 text-white dark:bg-stone-200 dark:text-stone-800' : 'bg-stone-300 text-stone-500 cursor-not-allowed dark:bg-stone-600 dark:text-stone-400'" :disabled="!editAllergies.trim()" @click="saveAllergies">保存</button>
                </div>
              </div>

              <!-- 特殊需求 -->
              <div class="rounded-lg border border-stone-100 bg-stone-50 px-3 py-2.5 dark:border-stone-700 dark:bg-[#1a1a1a]">
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-xs text-stone-400 dark:text-stone-500">🍼 特殊需求</div>
                    <div class="mt-0.5 text-sm font-medium text-stone-700 dark:text-stone-200">
                      {{ (() => { const raw = getProfileVal('special_needs'); if (!raw) return '未设置'; try { return JSON.parse(raw).join('、') } catch { return raw } })() }}
                    </div>
                  </div>
                  <button class="text-xs font-medium" :class="showEdit === 'special_needs' ? 'text-red-500 hover:text-red-700' : 'text-stone-400 hover:text-stone-600 dark:hover:text-stone-200'" @click="showEdit === 'special_needs' ? showEdit = null : startEditSpecialNeeds()">{{ showEdit === 'special_needs' ? '关闭' : '编辑' }}</button>
                </div>
                <div v-if="showEdit === 'special_needs'" class="mt-2">
                  <input v-model="editSpecialNeeds" placeholder="用顿号分隔，如：携带婴儿、行动不便" class="w-full rounded-lg border border-stone-200 bg-white px-2.5 py-1.5 text-sm outline-none focus:border-stone-400 dark:border-stone-600 dark:bg-[#2a2a2a] dark:text-stone-200" />
                  <div class="mt-1.5 flex flex-wrap gap-1">
                    <button v-for="opt in ['携带婴儿','携带幼儿','孕妇出行','行动不便','携带宠物','高血压','糖尿病','近视']" :key="opt"
                      class="rounded-full border border-stone-200 bg-white px-2 py-0.5 text-[10px] text-stone-500 hover:border-stone-400 dark:border-stone-600 dark:bg-[#2a2a2a] dark:text-stone-400"
                      @click="editSpecialNeeds = editSpecialNeeds ? editSpecialNeeds + '、' + opt : opt"
                    >{{ opt }}</button>
                  </div>
                  <button class="mt-2 rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-40 dark:disabled:opacity-40" :class="editSpecialNeeds.trim() ? 'bg-stone-800 text-white dark:bg-stone-200 dark:text-stone-800' : 'bg-stone-300 text-stone-500 cursor-not-allowed dark:bg-stone-600 dark:text-stone-400'" :disabled="!editSpecialNeeds.trim()" @click="saveSpecialNeeds">保存</button>
                </div>
              </div>

              <!-- 出行方式 -->
              <div class="rounded-lg border border-stone-100 bg-stone-50 px-3 py-2.5 dark:border-stone-700 dark:bg-[#1a1a1a]">
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-xs text-stone-400 dark:text-stone-500">🚗 出行方式偏好</div>
                    <div class="mt-0.5 text-sm font-medium text-stone-700 dark:text-stone-200">
                      {{ transportMap[getProfileVal('transport_preference')] || '灵活推荐' }}
                    </div>
                  </div>
                  <button class="text-xs text-stone-400 hover:text-stone-600 dark:hover:text-stone-200" @click="startEditTransport">编辑</button>
                </div>
                <div v-if="showEdit === 'transport'" class="mt-2 flex gap-1.5">
                  <button
                    v-for="(label, key) in transportMap" :key="key"
                    class="flex-1 rounded-lg border px-2 py-1.5 text-xs font-medium transition-colors"
                    :class="editTransport === key
                      ? 'border-stone-800 bg-stone-800 text-white dark:border-stone-200 dark:bg-stone-200 dark:text-stone-800'
                      : 'border-stone-200 bg-white text-stone-600 hover:border-stone-400 dark:border-stone-600 dark:bg-[#2a2a2a] dark:text-stone-300'"
                    @click="editTransport = key; savePref('travel_profile', 'transport_preference', key)"
                  >{{ label }}</button>
                </div>
              </div>
            </div>
          </div>

          <!-- ═══ 区域三：系统信息 ═══ -->
          <div v-if="systemPrefs.length > 0">
            <h4 class="mb-3 text-xs font-semibold uppercase text-stone-400 dark:text-stone-500">📍 系统信息</h4>
            <div class="space-y-1.5">
              <div
                v-for="p in systemPrefs"
                :key="p.id"
                class="flex items-center justify-between rounded-lg border border-stone-100 bg-stone-50 px-3 py-2 dark:border-stone-700 dark:bg-[#1a1a1a]"
              >
                <div>
                  <div class="text-xs text-stone-400 dark:text-stone-500">{{ p.key === 'departure_city' ? '出发地' : '当前城市' }}</div>
                  <div class="mt-0.5 text-sm font-medium text-stone-700 dark:text-stone-200">{{ p.value }}</div>
                </div>
                <span class="text-[10px] text-stone-300 dark:text-stone-600">自动获取</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
