<script setup lang="ts">
const emit = defineEmits<{ select: [style: string] }>()

interface StyleOption {
  key: string
  emoji: string
  label: string
  desc: string
}

const styles: StyleOption[] = [
  { key: 'compact',  emoji: '⚡', label: '紧凑打卡',  desc: '每天5-7景点' },
  { key: 'leisure',  emoji: '🌴', label: '休闲度假',  desc: '每天2-3景点' },
  { key: 'culture',  emoji: '📚', label: '深度文化',  desc: '历史博物馆' },
]
</script>

<template>
  <div class="flex items-center gap-1.5 px-1 py-1">
    <span class="text-[11px] text-stone-400 dark:text-stone-500 shrink-0">风格：</span>
    <button
      v-for="s in styles"
      :key="s.key"
      class="inline-flex items-center gap-1 rounded-full border border-stone-200 bg-white px-2.5 py-1 text-[11px] font-medium text-stone-600 transition-all hover:-translate-y-0.5 hover:border-amber-300 hover:bg-amber-50 hover:text-amber-700 hover:shadow-sm dark:border-stone-600 dark:bg-stone-700 dark:text-stone-300 dark:hover:border-amber-500 dark:hover:bg-stone-600 dark:hover:text-amber-400"
      @click="emit('select', s.key)"
    >
      <span>{{ s.emoji }}</span>
      <span>{{ s.label }}</span>
      <span class="hidden text-[10px] text-stone-400 sm:inline dark:text-stone-500">· {{ s.desc }}</span>
    </button>
  </div>
</template>
