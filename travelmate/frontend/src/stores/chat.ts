import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Message } from '@/types/chat'
import api from '@/api/client'
import { getDeviceId } from '@/utils/device'

interface Session {
  session_id: string
  title: string
  message_count: number
  last_message: string
  created_at: string
  updated_at: string
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const isLoading = ref(false)
  const sessionId = ref<string>('default')
  const sessions = ref<Session[]>([])

  function addMessage(msg: Message) {
    messages.value.push(msg)
  }

  function addSystemMessage(content: string) {
    addMessage({
      id: crypto.randomUUID(),
      role: 'system',
      content,
      timestamp: Date.now(),
      type: 'text',
    })
  }

  function addProactiveMessage(content: string, msgType: string = 'proactive') {
    addMessage({
      id: crypto.randomUUID(),
      role: 'assistant',
      content,
      timestamp: Date.now(),
      type: 'proactive',
      metadata: { proactive_type: msgType },
    })
  }

  function deleteMessage(id: string) {
    messages.value = messages.value.filter(m => m.id !== id)
  }

  function markFailed(id: string, errorType: Message['errorType'] = 'server') {
    const msg = messages.value.find(m => m.id === id)
    if (msg) {
      msg.failed = true
      msg.errorType = errorType
    }
  }

  async function retryMessage(id: string) {
    const msg = messages.value.find(m => m.id === id)
    if (!msg || !msg.failed) return

    msg.failed = false
    msg.errorType = undefined
    await sendMessage(msg.content, false, id)
  }

  async function regenerateMessage(id: string) {
    // 找到这条 assistant 消息之前的那条 user 消息
    const idx = messages.value.findIndex(m => m.id === id)
    if (idx < 0) return

    // 从当前消息往前找最近的 user 消息
    let userMsg: Message | undefined
    for (let i = idx - 1; i >= 0; i--) {
      if (messages.value[i].role === 'user') {
        userMsg = messages.value[i]
        break
      }
    }
    if (!userMsg) return

    // 删除当前 assistant 消息（重新生成会替换它）
    messages.value.splice(idx, 1)
    await sendMessage(userMsg.content, false, userMsg.id)
  }

  async function loadSessions() {
    try {
      const res = await api.get('/sessions', { params: { device_id: getDeviceId() } })
      sessions.value = res.data.sessions ?? []
    } catch {
      // 静默失败
    }
  }

  async function createSession(title?: string): Promise<string> {
    const res = await api.post('/sessions', {
      device_id: getDeviceId(),
      title: title ?? '新会话',
    })
    const newId = res.data.session_id as string
    sessionId.value = newId
    messages.value = []
    await loadSessions()
    return newId
  }

  async function switchSession(id: string) {
    if (id === sessionId.value) return
    sessionId.value = id
    isLoading.value = true
    try {
      const res = await api.get(`/sessions/${id}/messages`, {
        params: { device_id: getDeviceId() },
      })
      const raw = res.data.messages ?? []
      messages.value = raw.map((m: any) => ({
        id: crypto.randomUUID(),
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at).getTime(),
        type: 'text',
      }))
    } catch {
      messages.value = []
      addSystemMessage('加载会话消息失败')
    } finally {
      isLoading.value = false
    }
  }

  async function deleteSession(id: string) {
    try {
      await api.delete(`/sessions/${id}`, { params: { device_id: getDeviceId() } })
      sessions.value = sessions.value.filter(s => s.session_id !== id)
      if (id === sessionId.value) {
        if (sessions.value.length > 0) {
          await switchSession(sessions.value[0].session_id)
        } else {
          await createSession()
        }
      }
    } catch {
      // 静默失败
    }
  }

  async function sendMessage(content: string, appendUserMsg = true, existingUserMsgId?: string) {
    const userMsgId = existingUserMsgId ?? crypto.randomUUID()
    if (appendUserMsg) {
      addMessage({
        id: userMsgId,
        role: 'user',
        content,
        timestamp: Date.now(),
        type: 'text',
      })
    }

    isLoading.value = true
    try {
      const res = await api.post('/chat', {
        message: content,
        device_id: getDeviceId(),
        session_id: sessionId.value,
      })
      const data = res.data
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.reply,
        timestamp: Date.now(),
        type: data.message_type ?? 'text',
        metadata: data.metadata,
      })
      loadSessions()
    } catch (err: any) {
      // 无 response 即请求未到达服务器 → 网络错误
      const noResponse = !err.response
      const isNetwork = noResponse
        || err?.code === 'ERR_NETWORK'
        || err?.code === 'ECONNREFUSED'
        || err?.message?.includes('Network Error')
        || err?.message?.includes('Connection refused')
      const isTimeout = err?.code === 'ECONNABORTED' || err?.message?.includes('timeout')

      let errorType: Message['errorType'] = 'server'
      if (isNetwork) errorType = 'network'
      else if (isTimeout) errorType = 'timeout'

      console.error('[sendMessage] 请求失败:', { errorType, code: err?.code, message: err?.message, noResponse })
      markFailed(userMsgId, errorType)
    } finally {
      isLoading.value = false
    }
  }

  return {
    messages,
    isLoading,
    sessionId,
    sessions,
    sendMessage,
    addMessage,
    addSystemMessage,
    addProactiveMessage,
    deleteMessage,
    retryMessage,
    regenerateMessage,
    loadSessions,
    createSession,
    switchSession,
    deleteSession,
  }
})
