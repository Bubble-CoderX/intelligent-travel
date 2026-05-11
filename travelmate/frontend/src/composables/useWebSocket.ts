import { ref, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'

export function useWebSocket(deviceId: string) {
  const connected = ref(false)
  const chatStore = useChatStore()
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function connect() {
    ws = new WebSocket(`ws://localhost:8000/ws/${deviceId}`)

    ws.onopen = () => {
      connected.value = true
      console.log('[WS] 已连接')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'pong') return
        chatStore.addProactiveMessage(data.content, data.type)
      } catch {
        console.warn('[WS] 消息解析失败', event.data)
      }
    }

    ws.onclose = () => {
      connected.value = false
      console.log('[WS] 连接断开，5秒后重连')
      reconnectTimer = setTimeout(connect, 5000)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  onMounted(connect)

  onUnmounted(() => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
  })

  return { connected }
}
