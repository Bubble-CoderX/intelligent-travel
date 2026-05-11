import { ref } from 'vue'

export function useSpeechSynthesis() {
  const isSpeaking = ref(false)
  const isSupported = ref('speechSynthesis' in window)

  function speak(text: string, lang = 'zh-CN') {
    if (!isSupported.value) return
    speechSynthesis.cancel()

    // 去除 Markdown 格式符号，只保留纯文本
    const cleanText = text
      .replace(/#{1,6}\s/g, '')
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/`(.*?)`/g, '$1')
      .replace(/\[(.*?)\]\(.*?\)/g, '$1')
      .replace(/[>|\-|•]/g, '')
      .replace(/\n{2,}/g, '。')
      .replace(/\n/g, '，')
      .trim()

    if (!cleanText) return

    const utterance = new SpeechSynthesisUtterance(cleanText)
    utterance.lang = lang
    utterance.rate = 1.0
    utterance.onend = () => { isSpeaking.value = false }
    utterance.onerror = () => { isSpeaking.value = false }

    isSpeaking.value = true
    speechSynthesis.speak(utterance)
  }

  function stop() {
    speechSynthesis.cancel()
    isSpeaking.value = false
  }

  return { isSpeaking, isSupported, speak, stop }
}
