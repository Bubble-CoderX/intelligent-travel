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
        type: m.intent === 'TRIP_PLAN' ? 'card' : 'text',
        metadata: m.metadata ?? undefined,
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

  async function renameSession(id: string, title: string) {
    try {
      await api.put(`/sessions/${id}/rename`, { title }, { params: { device_id: getDeviceId() } })
      const s = sessions.value.find(s => s.session_id === id)
      if (s) s.title = title
    } catch {
      // 静默失败
    }
  }

  async function sendMessage(content: string, appendUserMsg = true, existingUserMsgId?: string, tripStyle?: string) {
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
    const assistantMsgId = crypto.randomUUID()

    try {
      // O9: 尝试流式输出
      const payload: Record<string, any> = {
        message: content,
        device_id: getDeviceId(),
        session_id: sessionId.value,
      }
      if (tripStyle) payload.trip_style = tripStyle

      const response = await fetch('http://localhost:8000/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      const decoder = new TextDecoder()
      let fullContent = ''
      let intent = 'CHAT'
      let msgType = 'text'
      let metadata: Record<string, unknown> = {}
      let buffer = ''

      // 先创建空的 assistant 消息（显示打字中）
      addMessage({
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
        type: 'text',
      })

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const dataStr = line.slice(6).trim()
          if (dataStr === '[DONE]') continue

          try {
            const evt = JSON.parse(dataStr)
            if (evt.type === 'chunk') {
              fullContent += evt.content
              // 更新消息内容（实时打字效果）
              const msg = messages.value.find(m => m.id === assistantMsgId)
              if (msg) msg.content = fullContent
            } else if (evt.type === 'full') {
              // 整体返回（TRIP_PLAN 等）
              fullContent = evt.content
              intent = evt.intent ?? 'CHAT'
              metadata = evt.metadata ?? {}
              msgType = intent === 'TRIP_PLAN' ? 'card' : 'text'
              const msg = messages.value.find(m => m.id === assistantMsgId)
              if (msg) {
                msg.content = fullContent
                msg.type = msgType as any
                msg.metadata = metadata
              }
            } else if (evt.type === 'error') {
              fullContent = evt.content
              const msg = messages.value.find(m => m.id === assistantMsgId)
              if (msg) { msg.content = fullContent; (msg as any).failed = true }
            }
          } catch { /* ignore parse errors */ }
        }
      }

      // 流结束，保存消息（通过非流式接口同步）
      // 注意：流式接口的保存由后端处理，这里不需要额外保存
      loadSessions()

    } catch (err: any) {
      // 流式失败 → 降级到非流式
      console.warn('[Stream] 流式失败，降级到非流式:', err?.message)
      try {
        const payload: Record<string, any> = {
          message: content,
          device_id: getDeviceId(),
          session_id: sessionId.value,
        }
        if (tripStyle) payload.trip_style = tripStyle

        const res = await api.post('/chat', payload)
        const data = res.data

        // 移除流式创建的空消息，替换为完整回复
        const idx = messages.value.findIndex(m => m.id === assistantMsgId)
        if (idx >= 0) {
          messages.value[idx].content = data.reply
          messages.value[idx].type = data.message_type ?? 'text'
          messages.value[idx].metadata = data.metadata
        } else {
          addMessage({
            id: assistantMsgId,
            role: 'assistant',
            content: data.reply,
            timestamp: Date.now(),
            type: data.message_type ?? 'text',
            metadata: data.metadata,
          })
        }
        loadSessions()
      } catch (err2: any) {
        const noResponse = !err2.response
        const isNetwork = noResponse || err2?.code === 'ERR_NETWORK' || err2?.message?.includes('Network Error')
        const isTimeout = err2?.code === 'ECONNABORTED' || err2?.message?.includes('timeout')
        let errorType: Message['errorType'] = 'server'
        if (isNetwork) errorType = 'network'
        else if (isTimeout) errorType = 'timeout'

        const idx = messages.value.findIndex(m => m.id === assistantMsgId)
        if (idx >= 0) {
          messages.value[idx].content = '抱歉，处理消息时出现了问题。'
          messages.value[idx].failed = true
          ;(messages.value[idx] as any).errorType = errorType
        }
      }
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
    renameSession,
  }
})
