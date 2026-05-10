<script setup lang="ts">
defineProps<{
  title: string
  destination: string
  days: number
  budget: number
  summary: string
}>()
</script>

<template>
  <div class="rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50 to-white p-5 shadow-sm">
    <div class="mb-3 flex items-center justify-between">
      <h3 class="text-base font-semibold text-gray-900">{{ title }}</h3>
      <span class="rounded-full bg-blue-100 px-3 py-0.5 text-xs font-medium text-blue-700">
        {{ days }} 天
      </span>
    </div>
    <p class="mb-2 text-sm text-gray-600">目的地：{{ destination }}</p>
    <p class="mb-3 text-sm leading-relaxed text-gray-700">{{ summary }}</p>
    <div class="flex items-center justify-between border-t pt-3">
      <span class="text-xs text-gray-400">预估预算</span>
      <span class="text-lg font-bold text-blue-600">¥{{ budget.toFixed(0) }}</span>
    </div>
  </div>
</template>
