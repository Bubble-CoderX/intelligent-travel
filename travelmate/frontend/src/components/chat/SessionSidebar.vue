<script setup lang="ts">
import { useChatStore } from '@/stores/chat'

const store = useChatStore()

function formatTime(ts: string) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH}小时前`
  const diffD = Math.floor(diffH / 24)
  if (diffD < 7) return `${diffD}天前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<template>
  <aside class="flex h-full w-64 flex-col border-r border-stone-200 bg-stone-50 dark:border-stone-700 dark:bg-stone-900">
    <!-- 顶栏 -->
    <div class="flex items-center justify-between border-b border-stone-200 px-4 py-3 dark:border-stone-700">
      <span class="text-xs font-semibold uppercase tracking-wide text-stone-400 dark:text-stone-500">会话列表</span>
      <button
        class="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500 text-white text-sm font-bold hover:bg-amber-600 transition-colors"
        title="新建会话"
        @click="store.createSession()"
      >
        +
      </button>
    </div>

    <!-- 会话列表 -->
    <div class="flex-1 overflow-y-auto py-1">
      <div v-if="store.sessions.length === 0" class="px-4 py-8 text-center text-xs text-stone-400 dark:text-stone-500">
        暂无会话，点击 + 新建
      </div>

      <div
        v-for="s in store.sessions"
        :key="s.session_id"
        class="group flex w-full cursor-pointer items-start gap-2.5 border-l-2 px-3 py-2.5 text-left transition-colors hover:bg-stone-100 dark:hover:bg-stone-800"
        :class="store.sessionId === s.session_id
          ? 'border-amber-500 bg-amber-50 dark:bg-amber-950'
          : 'border-transparent'"
        @click="store.switchSession(s.session_id)"
      >
        <span class="mt-0.5 shrink-0 text-base opacity-70">
          {{ store.sessionId === s.session_id ? '💬' : '🗨️' }}
        </span>

        <div class="min-w-0 flex-1">
          <div
            class="truncate text-sm font-medium"
            :class="store.sessionId === s.session_id ? 'text-amber-700 dark:text-amber-300' : 'text-stone-700 dark:text-stone-200'"
          >
            {{ s.title || '新会话' }}
          </div>
          <div class="mt-0.5 flex items-center gap-1 text-[11px] text-stone-400 dark:text-stone-500">
            <span>{{ s.message_count }} 条</span>
            <span v-if="s.updated_at">· {{ formatTime(s.updated_at) }}</span>
          </div>
        </div>

        <button
          class="shrink-0 mt-0.5 rounded p-0.5 text-stone-300 opacity-0 transition-all group-hover:opacity-100 hover:bg-red-50 hover:text-red-400 dark:text-stone-600 dark:hover:bg-red-950 dark:hover:text-red-400"
          title="删除会话"
          @click.stop="store.deleteSession(s.session_id)"
        >
          <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  </aside>
</template>
