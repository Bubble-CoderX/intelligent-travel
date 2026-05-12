<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()

const renamingId = ref<string | null>(null)
const renameInput = ref('')

function startRename(s: { session_id: string; title: string }) {
  renamingId.value = s.session_id
  renameInput.value = s.title || '新会话'
  // 等 DOM 渲染完毕后自动聚焦并全选
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

function handleRenameKeydown(e: KeyboardEvent, sessionId: string) {
  if (e.key === 'Enter') {
    e.preventDefault()
    commitRename(sessionId)
  } else if (e.key === 'Escape') {
    cancelRename()
  }
}

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
          <!-- 重命名输入框 -->
          <div v-if="renamingId === s.session_id" class="flex items-center gap-1">
            <input
              :id="'rename-input-' + s.session_id"
              v-model="renameInput"
              class="min-w-0 flex-1 rounded border border-amber-400 bg-white px-1.5 py-0.5 text-sm font-medium text-stone-800 outline-none ring-1 ring-amber-200 dark:bg-stone-700 dark:text-stone-100"
              @keydown="handleRenameKeydown($event, s.session_id)"
              @blur="commitRename(s.session_id)"
              @click.stop
            />
            <button
              class="shrink-0 rounded p-0.5 text-amber-500 hover:bg-amber-50"
              title="确认"
              @click.stop="commitRename(s.session_id)"
            >
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
            </button>
          </div>

          <!-- 正常标题（双击进入重命名） -->
          <div
            v-else
            class="truncate text-sm font-medium"
            :class="store.sessionId === s.session_id ? 'text-amber-700 dark:text-amber-300' : 'text-stone-700 dark:text-stone-200'"
            @dblclick.stop="startRename(s)"
            title="双击重命名"
          >
            {{ s.title || '新会话' }}
          </div>

          <div class="mt-0.5 flex items-center gap-1 text-[11px] text-stone-400 dark:text-stone-500">
            <span>{{ s.message_count }} 条</span>
            <span v-if="s.updated_at">· {{ formatTime(s.updated_at) }}</span>
          </div>
        </div>

        <!-- 操作按钮组（hover 显示） -->
        <div class="flex shrink-0 items-center gap-0.5 opacity-0 transition-all group-hover:opacity-100">
          <!-- 重命名按钮 -->
          <button
            class="rounded p-0.5 text-stone-300 hover:bg-stone-100 hover:text-amber-500 dark:text-stone-600 dark:hover:bg-stone-700 dark:hover:text-amber-400"
            title="重命名"
            @click.stop="startRename(s)"
          >
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <!-- 删除按钮 -->
          <button
            class="rounded p-0.5 text-stone-300 hover:bg-red-50 hover:text-red-400 dark:text-stone-600 dark:hover:bg-red-950 dark:hover:text-red-400"
            title="删除会话"
            @click.stop="store.deleteSession(s.session_id)"
          >
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>
