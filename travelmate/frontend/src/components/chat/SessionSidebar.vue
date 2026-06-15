<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()
const router = useRouter()
const props = defineProps<{ dark?: boolean; toggleDark?: () => void }>()

const renamingId = ref<string | null>(null)
const renameInput = ref('')

function startRename(s: { session_id: string; title: string }) {
  renamingId.value = s.session_id
  renameInput.value = s.title || '新会话'
  setTimeout(() => {
    const el = document.getElementById('rename-input-' + s.session_id) as HTMLInputElement | null
    if (el) { el.focus(); el.select() }
  }, 50)
}

function commitRename(sessionId: string) {
  const newTitle = renameInput.value.trim()
  if (newTitle) {
    store.renameSession(sessionId, newTitle)
  }
  renamingId.value = null
}

function cancelRename() {
  renamingId.value = null
}

function formatSessionTime(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  if (isToday) return `${h}:${m}`
  const month = d.getMonth() + 1
  const day = d.getDate()
  return `${month}/${day} ${h}:${m}`
}

function handleRenameKeydown(e: KeyboardEvent, sessionId: string) {
  if (e.key === 'Enter') {
    e.preventDefault()
    commitRename(sessionId)
  } else if (e.key === 'Escape') {
    cancelRename()
  }
}
</script>

<template>
  <aside class="flex h-full w-64 flex-col bg-white text-stone-700 border-r border-stone-200 dark:bg-[#212121] dark:text-stone-300 dark:border-stone-700">
    <!-- 上段：导航区（固定，不滚动） -->
    <div class="flex items-center justify-between px-3 pt-3 pb-2">
      <button class="rounded-lg p-1.5 text-stone-400 transition-colors hover:bg-stone-100 hover:text-stone-600 dark:hover:bg-[#2f2f2f] dark:hover:text-stone-200" @click="$emit('toggleSidebar')" title="收起侧边栏">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" /></svg>
      </button>
      <button class="rounded-lg p-1.5 text-stone-400 transition-colors hover:bg-stone-100 hover:text-stone-600 dark:hover:bg-[#2f2f2f] dark:hover:text-stone-200" title="新建会话" @click="store.createSession(); router.push('/')">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
      </button>
    </div>

    <nav class="flex-shrink-0 px-2 py-1 space-y-0.5">
      <button class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm transition-colors" :class="$route?.path === '/' ? 'bg-stone-100 text-stone-800 dark:bg-[#2f2f2f] dark:text-stone-100' : 'text-stone-500 hover:bg-stone-50 hover:text-stone-700 dark:text-stone-400 dark:hover:bg-[#2a2a2a]'" @click="store.createSession(); router.push('/')">
        <span class="text-base">💬</span> 新建对话
      </button>
      <button class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm transition-colors" :class="$route?.path === '/trips' ? 'bg-stone-100 text-stone-800 dark:bg-[#2f2f2f] dark:text-stone-100' : 'text-stone-500 hover:bg-stone-50 hover:text-stone-700 dark:text-stone-400 dark:hover:bg-[#2a2a2a]'" @click="router.push('/trips')">
        <span class="text-base">📋</span> 历史行程
      </button>
      <button class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm transition-colors" :class="$route?.path === '/profile' ? 'bg-stone-100 text-stone-800 dark:bg-[#2f2f2f] dark:text-stone-100' : 'text-stone-500 hover:bg-stone-50 hover:text-stone-700 dark:text-stone-400 dark:hover:bg-[#2a2a2a]'" @click="router.push('/profile')">
        <span class="text-base">👤</span> 我的档案
      </button>
      <button class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm transition-colors" :class="$route?.path === '/knowledge' ? 'bg-stone-100 text-stone-800 dark:bg-[#2f2f2f] dark:text-stone-100' : 'text-stone-500 hover:bg-stone-50 hover:text-stone-700 dark:text-stone-400 dark:hover:bg-[#2a2a2a]'" @click="router.push('/knowledge')">
        <span class="text-base">📚</span> 知识库浏览
      </button>
    </nav>

    <!-- 分隔线 -->
    <div class="border-t border-stone-200 dark:border-stone-700 mx-3"></div>

    <!-- 中段：历史对话列表（占满剩余空间，可滚动） -->
    <div class="flex-1 overflow-y-auto px-2 py-2">
      <p class="px-2.5 py-1 text-xs font-medium uppercase" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">历史对话</p>

      <div v-if="store.sessions.length === 0" class="px-3 py-8 text-center text-xs text-stone-400 dark:text-stone-500">暂无会话</div>

      <div v-for="s in store.sessions" :key="s.session_id" class="group flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors" :class="store.sessionId === s.session_id ? 'bg-stone-100 text-stone-800 dark:bg-[#2f2f2f] dark:text-stone-100' : 'text-stone-500 hover:bg-stone-100 hover:text-stone-700 dark:text-stone-400 dark:hover:bg-[#2a2a2a] dark:hover:text-stone-200'" @click="store.switchSession(s.session_id)">
        <div v-if="renamingId === s.session_id" class="flex flex-1 items-center gap-1">
          <input :id="'rename-input-' + s.session_id" v-model="renameInput" class="min-w-0 flex-1 rounded border border-stone-300 bg-white px-1.5 py-0.5 text-sm text-stone-800 outline-none ring-1 ring-stone-300 dark:border-stone-500 dark:bg-[#171717] dark:text-stone-100 dark:ring-stone-500" @keydown="handleRenameKeydown($event, s.session_id)" @blur="commitRename(s.session_id)" @click.stop />
          <button class="shrink-0 rounded p-0.5 text-stone-400 hover:text-stone-600 dark:hover:text-stone-200" title="确认" @click.stop="commitRename(s.session_id)">
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
          </button>
        </div>
        <template v-else>
          <div class="min-w-0 flex-1">
            <span class="block truncate text-sm">{{ s.title || '新会话' }}</span>
            <span class="block text-[10px] mt-0.5" :class="props.dark ? 'text-stone-600' : 'text-stone-400'">{{ formatSessionTime(s.created_at) }}</span>
          </div>
          <div class="flex shrink-0 items-center gap-0.5 opacity-0 transition-all group-hover:opacity-100">
            <button class="rounded p-0.5 text-stone-400 hover:text-stone-600 dark:text-stone-500 dark:hover:text-stone-200" title="重命名" @click.stop="startRename(s)">
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
            </button>
            <button class="rounded p-0.5 text-stone-400 hover:text-red-400 dark:text-stone-500 dark:hover:text-red-400" title="删除" @click.stop="store.deleteSession(s.session_id)">
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </template>
      </div>
    </div>

    <!-- 分隔线 -->
    <div class="border-t border-stone-200 dark:border-stone-700 mx-3"></div>

    <!-- 下段：系统功能区（固定，不滚动） -->
    <div class="flex-shrink-0 px-3 py-2 space-y-0.5">
      <button class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700 dark:text-stone-400 dark:hover:bg-[#2f2f2f] dark:hover:text-stone-200" @click="$emit('toggleBatchExpand')">
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
        扩充知识库
      </button>
      <button class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700 dark:text-stone-400 dark:hover:bg-[#2f2f2f] dark:hover:text-stone-200" @click="$emit('togglePrefs')">
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
        偏好设置
      </button>
      <button v-if="props.toggleDark" class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700 dark:text-stone-400 dark:hover:bg-[#2f2f2f] dark:hover:text-stone-200" @click="props.toggleDark()">
        <svg v-if="!props.dark" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>
        <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
        {{ props.dark ? '浅色模式' : '暗色模式' }}
      </button>
    </div>
  </aside>
</template>
