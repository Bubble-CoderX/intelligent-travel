import { ref } from 'vue'

export function useSpeechRecognition() {
  const isListening = ref(false)
  const transcript = ref('')
  const errorMsg = ref('')
  const isSupported = ref('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)

  let recognition: any = null
  let silenceTimer: ReturnType<typeof setTimeout> | null = null

  function initRecognition() {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) return null

    const rec = new SpeechRecognition()
    rec.lang = 'zh-CN'
    rec.continuous = true
    rec.interimResults = true

    rec.onresult = (event: any) => {
      // 拼接所有最终结果（isFinal=true），忽略中间结果
      const parts: string[] = []
      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          parts.push(result[0].transcript)
        }
      }
      if (parts.length > 0) {
        transcript.value = parts.join('')
      }

      // 如果所有结果都是最终结果，自动停止
      if (event.results[event.results.length - 1]?.isFinal) {
        clearSilenceTimer()
        silenceTimer = setTimeout(() => stop(), 1500)
      }
    }

    rec.onerror = (event: any) => {
      const errMap: Record<string, string> = {
        'no-speech': '未检测到语音，请检查麦克风是否正常工作',
        'aborted': '识别中断',
        'audio-capture': '未找到麦克风设备',
        'network': '语音识别需要网络连接',
        'not-allowed': '麦克风权限未授权，请在浏览器设置中允许',
        'service-not-allowed': '语音服务不可用',
        'bad-grammar': '语音识别语法错误',
        'language-not-supported': '不支持当前语言',
      }
      errorMsg.value = errMap[event.error] || `语音识别错误: ${event.error}`
      console.warn('[语音] 识别错误:', event.error, errorMsg.value)
      isListening.value = false
      clearSilenceTimer()
      // 错误后重建 recognition 对象
      recognition = null
    }

    rec.onend = () => {
      isListening.value = false
      clearSilenceTimer()
    }

    return rec
  }

  function clearSilenceTimer() {
    if (silenceTimer) {
      clearTimeout(silenceTimer)
      silenceTimer = null
    }
  }

  function start() {
    if (!isSupported.value) return
    recognition = recognition || initRecognition()
    if (!recognition) return
    transcript.value = ''
    errorMsg.value = ''
    try {
      recognition.start()
      isListening.value = true
    } catch {
      // recognition was already started, ignore
    }
  }

  function stop() {
    clearSilenceTimer()
    recognition?.stop()
    isListening.value = false

    // 清理标点符号
    transcript.value = transcript.value
      .replace(/[。，！？、；：""''（）【】《》…—·\s]+$/g, '')
      .trim()
  }

  return { isListening, transcript, errorMsg, isSupported, start, stop }
}
