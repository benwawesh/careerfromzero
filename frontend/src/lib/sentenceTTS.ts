import { useRef } from 'react'
import { apiFetch } from './apiFetch'

/**
 * Sentence-level streaming TTS.
 * As AI tokens arrive, complete sentences are sent to TTS immediately.
 * Audio plays in order — later sentences wait for earlier ones.
 */
export function useSentenceTTS(onPlayingChange?: (playing: boolean) => void) {
  const sentenceBufferRef = useRef('')
  // Ordered slots: null = TTS pending, '' = skip (error/empty), string = base64 audio
  const slotsRef = useRef<Array<string | null>>([])
  const playHeadRef = useRef(0)
  const isPlayingRef = useRef(false)

  const tryAdvanceRef = useRef<(() => void) | undefined>(undefined)
  tryAdvanceRef.current = () => {
    // Skip empty slots
    while (
      playHeadRef.current < slotsRef.current.length &&
      slotsRef.current[playHeadRef.current] === ''
    ) {
      playHeadRef.current++
    }
    if (playHeadRef.current >= slotsRef.current.length) {
      isPlayingRef.current = false
      onPlayingChange?.(false)
      return
    }
    const slot = slotsRef.current[playHeadRef.current]
    if (slot === null) {
      // Not ready yet — wait; will resume when this slot is filled
      isPlayingRef.current = false
      onPlayingChange?.(false)
      return
    }
    // Play this slot
    isPlayingRef.current = true
    onPlayingChange?.(true)
    playHeadRef.current++
    const audio = new Audio(`data:audio/mp3;base64,${slot}`)
    audio.onended = () => tryAdvanceRef.current?.()
    audio.onerror = () => tryAdvanceRef.current?.()
    audio.play().catch(() => tryAdvanceRef.current?.())
  }

  const speakText = async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed) return
    const slotIdx = slotsRef.current.length
    slotsRef.current.push(null) // reserve slot in order

    try {
      const res = await apiFetch('/api/guidance/tts/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: trimmed }),
      })
      if (res.ok) {
        const data = await res.json()
        slotsRef.current[slotIdx] = data.audio || ''
      } else {
        slotsRef.current[slotIdx] = ''
      }
    } catch {
      slotsRef.current[slotIdx] = ''
    }

    // Resume playback if we're waiting at this slot
    if (!isPlayingRef.current) {
      tryAdvanceRef.current?.()
    }
  }

  /** Call for each streaming token */
  const onToken = (token: string) => {
    sentenceBufferRef.current += token
    // Extract complete sentences ending with . ! ? followed by whitespace
    let match
    while ((match = sentenceBufferRef.current.match(/^(.+?[.!?])\s+([\s\S]*)$/))) {
      void speakText(match[1].trim())
      sentenceBufferRef.current = match[2]
    }
  }

  /** Call when the stream finishes — flushes any remaining buffer */
  const onStreamEnd = () => {
    const remaining = sentenceBufferRef.current.trim()
    if (remaining) void speakText(remaining)
    sentenceBufferRef.current = ''
  }

  /**
   * Speak pre-existing text (e.g. initial messages) sentence by sentence
   * so the first sentence starts playing immediately rather than waiting
   * for the entire paragraph to be processed by TTS.
   */
  const speakFull = (text: string) => {
    // Split on sentence boundaries (. ! ? followed by whitespace) and speak each part
    const parts = text.trim().split(/(?<=[.!?])\s+/)
    for (const part of parts) {
      if (part.trim()) void speakText(part.trim())
    }
  }

  /** Stop all audio and reset state */
  const stop = () => {
    slotsRef.current = []
    playHeadRef.current = 0
    isPlayingRef.current = false
    sentenceBufferRef.current = ''
    onPlayingChange?.(false)
  }

  return { onToken, onStreamEnd, speakText, speakFull, stop }
}
