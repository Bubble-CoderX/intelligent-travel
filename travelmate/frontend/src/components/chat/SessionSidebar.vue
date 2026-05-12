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
  <aside class="flex h-full w-64 flex-col bg-stone-50 border-r border-stone-200">
    <!-- 顶栏 -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-stone-200">
      <span class="text-xs font-semibold uppercase text-stone-400 tracking-wide">会话列表</span>
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
      <div v-if="store.sessions.length === 0" class="px-4 py-8 text-center text-xs text-stone-400">
        暂无会话，点击 + 新建
      </div>

      <div
        v-for="s in store.sessions"
        :key="s.session_id"
        class="group flex w-full items-start gap-2.5 px-3 py-2.5 text-left transition-colors hover:bg-stone-100 cursor-pointer"
        :class="store.sessionId === s.session_id
          ? 'bg-amber-50 border-l-2 border-amber-500'
          : 'border-l-2 border-transparent'"
        @click="store.switchSession(s.session_id)"
      >
        <!-- 会话图标 -->
        <span class="mt-0.5 shrink-0 text-base opacity-70">
          {{ store.sessionId === s.session_id ? '💬' : '🗨️' }}
        </span>

        <!-- 文字内容 -->
        <div class="min-w-0 flex-1">
          <div
            class="truncate text-sm font-medium"
            :class="store.sessionId === s.session_id ? 'text-amber-700' : 'text-stone-700'"
          >
            {{ s.title || '新会话' }}
          </div>
          <div class="mt-0.5 flex items-center gap-1 text-[11px] text-stone-400">
            <span>{{ s.message_count }} 条</span>
            <span v-if="s.updated_at">· {{ formatTime(s.updated_at) }}</span>
          </div>
        </div>

        <!-- 删除按钮 -->
        <button
          class="shrink-0 mt-0.5 rounded p-0.5 text-stone-300 opacity-0 group-hover:opacity-100 hover:bg-red-50 hover:text-red-400 transition-all"
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
