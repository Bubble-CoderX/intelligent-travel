<script setup lang="ts">
import { useRouter } from 'vue-router'
const props = defineProps<{ dark?: boolean; toggleDark?: () => void }>()
const router = useRouter()
</script>

<template>
  <div class="min-h-screen" :class="props.dark ? 'bg-[#212121]' : 'bg-stone-50'">
    <div class="sticky top-0 z-30 flex items-center gap-3 border-b px-5 py-3" :class="props.dark ? 'bg-[#212121] border-stone-700' : 'bg-white border-stone-200'">
      <button class="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 dark:hover:bg-[#2f2f2f]" @click="router.push('/')">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
      </button>
      <h1 class="text-lg font-semibold" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">📚 知识库浏览</h1>
    </div>
    <div class="flex items-center justify-center py-20 text-sm text-stone-400">
      知识库浏览页（Batch B 实现）
    </div>
  </div>
</template>
