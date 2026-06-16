export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  type: 'text' | 'card' | 'proactive'
  metadata?: Record<string, unknown>
  imageData?: string
  failed?: boolean
  errorType?: 'network' | 'server' | 'timeout'
}
