'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Topic {
  id: number
  order: number
  title: string
  description: string
  estimated_days: number
  status: 'pending' | 'in_progress' | 'complete'
  score: number | null
  passed: boolean | null
}

interface Session {
  id: string
  goal: string
  current_level: string
  time_commitment: string
  status: 'onboarding' | 'active' | 'complete'
  topics: Topic[]
  created_at: string
}

type ChatMsg = { role: 'alex' | 'user'; text: string }

// ─── Audio (singleton — stops previous before playing new) ───────────────────

let _activeAudio: HTMLAudioElement | null = null

function playAudio(base64: string): Promise<void> {
  return new Promise(resolve => {
    try {
      if (_activeAudio) {
        _activeAudio.pause()
        _activeAudio.src = ''
        _activeAudio = null
      }
      const audio = new Audio(`data:audio/mp3;base64,${base64}`)
      _activeAudio = audio
      audio.onended = () => { _activeAudio = null; resolve() }
      audio.onerror = () => { _activeAudio = null; resolve() }
      audio.play().catch(() => { _activeAudio = null; resolve() })
    } catch { resolve() }
  })
}

// ─── Voice Input (Whisper) ────────────────────────────────────────────────────

function getSupportedMimeType(): string {
  const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
  for (const t of types) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t)) return t
  }
  return ''
}

function mimeToExtension(mime: string): string {
  if (mime.includes('ogg')) return 'ogg'
  if (mime.includes('mp4')) return 'mp4'
  return 'webm'
}

function VoiceInput({
  onTranscript,
  disabled = false,
}: {
  onTranscript: (text: string) => void
  disabled?: boolean
}) {
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [micError, setMicError] = useState('')
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const startRecording = async () => {
    setMicError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = getSupportedMimeType()
      const mr = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
      const actualMime = mr.mimeType || mimeType
      mediaRecorderRef.current = mr
      chunksRef.current = []
      mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        if (chunksRef.current.length === 0) { setMicError('No audio recorded.'); setTranscribing(false); return }
        const blob = new Blob(chunksRef.current, { type: actualMime || 'audio/webm' })
        const ext = mimeToExtension(actualMime)
        setTranscribing(true)
        try {
          const formData = new FormData()
          formData.append('audio', blob, `recording.${ext}`)
          const res = await apiFetch('/api/interview/transcribe/', { method: 'POST', body: formData })
          if (res.ok) {
            const data = await res.json()
            if (data.text?.trim()) onTranscript(data.text.trim())
            else setMicError('No speech detected. Try again.')
          } else {
            const err = await res.json().catch(() => ({}))
            setMicError(err.error || 'Transcription failed.')
          }
        } catch { setMicError('Network error during transcription.') }
        setTranscribing(false)
      }
      mr.start()
      setRecording(true)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : ''
      if (msg.includes('Permission') || msg.includes('NotAllowed') || msg.includes('denied'))
        setMicError('Microphone access denied.')
      else if (msg.includes('NotFound') || msg.includes('Requested device not found'))
        setMicError('No microphone found.')
      else setMicError('Could not start recording.')
    }
  }

  const stopRecording = () => { mediaRecorderRef.current?.stop(); setRecording(false) }

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        onClick={recording ? stopRecording : startRecording}
        disabled={disabled || transcribing}
        title={recording ? 'Stop recording' : 'Speak your answer'}
        className={`px-3 py-3 rounded-xl font-semibold text-sm flex items-center gap-1.5 transition-all ${
          recording
            ? 'bg-red-500 text-white animate-pulse hover:bg-red-600'
            : transcribing
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200'
        }`}
      >
        {transcribing ? (
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-500" />
        ) : recording ? (
          '⏹'
        ) : (
          '🎤'
        )}
      </button>
      {micError && <p className="text-xs text-red-500 max-w-[120px] leading-tight">{micError}</p>}
    </div>
  )
}

// ─── Typing indicator ─────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex justify-start items-end gap-2">
      <AlexAvatar speaking={false} />
      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  )
}

// ─── Alex Avatar ──────────────────────────────────────────────────────────────

function AlexAvatar({ speaking }: { speaking: boolean }) {
  return (
    <div className={`relative flex-shrink-0 w-8 h-8 ${speaking ? 'mt-1' : 'mt-1'}`}>
      {speaking && (
        <span className="absolute inset-0 rounded-full bg-blue-400 opacity-40 animate-ping" />
      )}
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white text-xs font-bold shadow-sm">
        A
      </div>
    </div>
  )
}

// ─── Markdown renderer (simple) ───────────────────────────────────────────────

function renderMarkdown(text: string): string {
  return text
    .replace(/^#{1,3}\s+(.+)$/gm, '<strong>$1</strong>')   // # headings → bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')        // **bold**
    .replace(/\*(.+?)\*/g, '<em>$1</em>')                    // *italic*
    .replace(/\n/g, '<br />')                                 // newlines
}

// ─── Chat bubble ──────────────────────────────────────────────────────────────

function ChatBubble({ msg, speaking = false }: { msg: ChatMsg; speaking?: boolean }) {
  const isAlex = msg.role === 'alex'
  return (
    <div className={`flex items-end gap-2 ${isAlex ? 'justify-start' : 'justify-end'}`}>
      {isAlex && <AlexAvatar speaking={speaking} />}
      <div className={`max-w-2xl px-4 py-3 rounded-2xl text-sm leading-relaxed ${
        isAlex
          ? 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'
          : 'bg-blue-600 text-white rounded-br-sm whitespace-pre-wrap'
      }`}>
        {isAlex
          ? <span dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }} />
          : msg.text
        }
      </div>
    </div>
  )
}

// ─── Voice toggle button ──────────────────────────────────────────────────────

function VoiceToggle({ enabled, onChange }: { enabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!enabled)}
      title={enabled ? 'Voice on — click to turn off' : 'Voice off — click to turn on'}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
        enabled
          ? 'bg-blue-600 text-white shadow-sm'
          : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
      }`}
    >
      {enabled ? '🔊' : '🔇'}
      <span className="hidden sm:inline">{enabled ? 'Voice On' : 'Voice Off'}</span>
    </button>
  )
}

// ─── Chat Input ───────────────────────────────────────────────────────────────

function ChatInput({
  onSend,
  disabled,
  placeholder = 'Type your message...',
  voiceEnabled = false,
}: {
  onSend: (text: string) => void
  disabled: boolean
  placeholder?: string
  voiceEnabled?: boolean
}) {
  const [input, setInput] = useState('')

  const send = () => {
    const t = input.trim()
    if (!t || disabled) return
    setInput('')
    onSend(t)
  }

  const onVoiceTranscript = (text: string) => {
    setInput(prev => prev ? `${prev} ${text}` : text)
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2 items-end">
        {voiceEnabled && (
          <VoiceInput onTranscript={onVoiceTranscript} disabled={disabled} />
        )}
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          placeholder={voiceEnabled ? 'Speak or type your message...' : placeholder}
          rows={2}
          disabled={disabled}
          className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm resize-none"
        />
        <button
          onClick={send}
          disabled={disabled || !input.trim()}
          className="px-5 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed self-end"
        >
          Send
        </button>
      </div>
      {voiceEnabled && (
        <p className="text-xs text-gray-400 text-center">🎤 Tap mic → speak → tap again to stop. Alex will reply in voice too.</p>
      )}
    </div>
  )
}

// ─── Page wrapper ─────────────────────────────────────────────────────────────

export default function CoachingSessionPage() {
  return (
    <ProtectedRoute>
      <CoachingSession />
    </ProtectedRoute>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

function CoachingSession() {
  const params = useParams()
  const sessionId = params.id as string

  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [voiceEnabled, setVoiceEnabled] = useState(false)

  useEffect(() => { fetchSession() }, [sessionId])

  const fetchSession = async () => {
    setLoading(true)
    try {
      const res = await apiFetch(`/api/guidance/sessions/${sessionId}/`)
      if (res.ok) setSession(await res.json())
      else if (res.status === 404) setError('Session not found.')
      else setError('Failed to load session.')
    } catch {
      setError('Network error.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  )

  if (error || !session) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <p className="text-red-600 mb-4">{error || 'Session not found.'}</p>
        <Link href="/ai/career-guidance" className="text-blue-600 hover:underline">← Back</Link>
      </div>
    </div>
  )

  if (session.status === 'onboarding') {
    return <OnboardingChat session={session} onReady={fetchSession} voiceEnabled={voiceEnabled} onVoiceToggle={setVoiceEnabled} />
  }

  return <ActiveSession session={session} onRefresh={fetchSession} voiceEnabled={voiceEnabled} onVoiceToggle={setVoiceEnabled} />
}

// ─── Onboarding Chat ──────────────────────────────────────────────────────────

function OnboardingChat({
  session,
  onReady,
  voiceEnabled,
  onVoiceToggle,
}: {
  session: Session
  onReady: () => void
  voiceEnabled: boolean
  onVoiceToggle: (v: boolean) => void
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [sending, setSending] = useState(false)
  const [speakingIdx, setSpeakingIdx] = useState<number | null>(null)
  const [generatingRoadmap, setGeneratingRoadmap] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const loadedRef = useRef(false)

  useEffect(() => { loadGreeting() }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const addAlexMsg = async (text: string, audio: string | null) => {
    const idx = messages.length
    setMessages(prev => [...prev, { role: 'alex', text }])
    if (audio && voiceEnabled) {
      setSpeakingIdx(idx)
      await playAudio(audio)
      setSpeakingIdx(null)
    }
  }

  const loadGreeting = async () => {
    if (loadedRef.current) return
    loadedRef.current = true
    setSending(true)
    try {
      // Try to restore existing conversation first
      const histRes = await apiFetch(`/api/guidance/sessions/${session.id}/messages/`)
      if (histRes.ok) {
        const history: { role: string; content: string }[] = await histRes.json()
        if (history.length > 0) {
          setMessages(history.map(m => ({ role: m.role as 'alex' | 'user', text: m.content })))
          setSending(false)
          return
        }
      }
      // No history — start fresh with greeting
      const res = await apiFetch(`/api/guidance/sessions/${session.id}/onboarding/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: '', include_audio: voiceEnabled }),
      })
      if (res.ok) {
        const data = await res.json()
        await addAlexMsg(data.response, data.audio)
      }
    } catch {}
    setSending(false)
  }

  const send = async (text: string) => {
    setError('')
    setMessages(prev => [...prev, { role: 'user', text }])
    setSending(true)
    try {
      const res = await apiFetch(`/api/guidance/sessions/${session.id}/onboarding/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, include_audio: voiceEnabled }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        setError(d.error || 'Something went wrong.')
        setSending(false)
        return
      }
      const data = await res.json()
      await addAlexMsg(data.response, data.audio)

      if (data.start_roadmap) {
        setSending(false)
        setGeneratingRoadmap(true)
        await generateRoadmap()
        return
      }
    } catch { setError('Network error.') }
    setSending(false)
  }

  const generateRoadmap = async () => {
    try {
      const res = await apiFetch(`/api/guidance/sessions/${session.id}/start-roadmap/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      if (res.ok) onReady()
      else { setError('Failed to generate your roadmap. Please try again.'); setGeneratingRoadmap(false) }
    } catch { setError('Network error while generating roadmap.'); setGeneratingRoadmap(false) }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow flex-shrink-0">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <Link href="/ai/career-guidance" className="text-gray-500 hover:text-gray-900 text-sm">← Career Coach</Link>
            <h1 className="text-base font-bold text-gray-900 mt-0.5 truncate">{session.goal}</h1>
          </div>
          <VoiceToggle enabled={voiceEnabled} onChange={onVoiceToggle} />
        </div>
      </header>

      {/* Voice hint banner */}
      {voiceEnabled && (
        <div className="bg-blue-50 border-b border-blue-100 px-4 py-2 text-center text-xs text-blue-600 font-medium">
          🔊 Voice mode on — Alex will speak to you. Use 🎤 to reply by voice.
        </div>
      )}

      <div className="flex-1 overflow-y-auto max-w-3xl w-full mx-auto px-4 py-6 space-y-4">
        {messages.map((m, i) => (
          <ChatBubble key={i} msg={m} speaking={speakingIdx === i} />
        ))}
        {(sending || generatingRoadmap) && <TypingIndicator />}
        {generatingRoadmap && (
          <div className="flex justify-center">
            <div className="bg-blue-50 border border-blue-200 text-blue-700 px-5 py-3 rounded-xl text-sm font-medium animate-pulse">
              ✨ Building your personalised roadmap...
            </div>
          </div>
        )}
        {error && <p className="text-center text-sm text-red-600">{error}</p>}
        <div ref={bottomRef} />
      </div>

      <div className="flex-shrink-0 bg-white border-t border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <ChatInput
            onSend={send}
            disabled={sending || generatingRoadmap}
            placeholder="Tell Alex about yourself..."
            voiceEnabled={voiceEnabled}
          />
        </div>
      </div>
    </div>
  )
}

// ─── Active Session ───────────────────────────────────────────────────────────

function ActiveSession({
  session,
  onRefresh,
  voiceEnabled,
  onVoiceToggle,
}: {
  session: Session
  onRefresh: () => void
  voiceEnabled: boolean
  onVoiceToggle: (v: boolean) => void
}) {
  const currentTopic = session.topics.find(t => t.status === 'in_progress') || session.topics.find(t => t.status === 'pending')
  const [activeView, setActiveView] = useState<'lesson' | 'quiz' | 'chat'>('lesson')
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(currentTopic || null)

  useEffect(() => {
    if (selectedTopic) {
      const updated = session.topics.find(t => t.id === selectedTopic.id)
      if (updated) setSelectedTopic(updated)
    }
  }, [session])

  const handleTopicSelect = (topic: Topic) => {
    setSelectedTopic(topic)
    setActiveView('lesson')
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow flex-shrink-0">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div className="min-w-0">
            <Link href="/ai/career-guidance" className="text-gray-500 hover:text-gray-900 text-sm">← Career Coach</Link>
            <h1 className="text-base font-bold text-gray-900 mt-0.5 truncate">{session.goal}</h1>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {session.status === 'complete' && (
              <span className="text-xs bg-green-100 text-green-700 px-3 py-1 rounded-full font-medium">Complete!</span>
            )}
            <VoiceToggle enabled={voiceEnabled} onChange={onVoiceToggle} />
            <button
              onClick={() => { setSelectedTopic(null); setActiveView('chat') }}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                activeView === 'chat' && !selectedTopic
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Ask Alex
            </button>
          </div>
        </div>
      </header>

      {voiceEnabled && (
        <div className="bg-blue-50 border-b border-blue-100 px-4 py-2 text-center text-xs text-blue-600 font-medium">
          🔊 Voice mode on — Alex will speak to you. Use 🎤 to reply by voice.
        </div>
      )}

      <div className="flex-1 flex max-w-6xl w-full mx-auto overflow-hidden">
        {/* Sidebar */}
        <aside className="w-72 flex-shrink-0 border-r border-gray-200 bg-white overflow-y-auto hidden md:block">
          <div className="p-4">
            <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Your Roadmap</h2>
            <div className="space-y-2">
              {session.topics.map(t => (
                <button
                  key={t.id}
                  onClick={() => handleTopicSelect(t)}
                  disabled={t.status === 'pending'}
                  className={`w-full text-left px-3 py-3 rounded-xl transition-all text-sm ${
                    selectedTopic?.id === t.id
                      ? 'bg-blue-50 border border-blue-200'
                      : t.status === 'complete'
                      ? 'bg-green-50 hover:bg-green-100 border border-transparent'
                      : t.status === 'in_progress'
                      ? 'bg-yellow-50 hover:bg-yellow-100 border border-transparent'
                      : 'bg-gray-50 border border-transparent opacity-50 cursor-not-allowed'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="flex-shrink-0 text-base">
                      {t.status === 'complete' ? '✅' : t.status === 'in_progress' ? '📖' : '🔒'}
                    </span>
                    <div className="min-w-0">
                      <p className="font-medium text-gray-800 truncate">{t.title}</p>
                      <p className="text-xs text-gray-400">~{t.estimated_days}d</p>
                    </div>
                    {t.score !== null && (
                      <span className={`ml-auto text-xs font-bold flex-shrink-0 ${t.passed ? 'text-green-600' : 'text-red-500'}`}>
                        {t.score}%
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-4 pt-4 border-t border-gray-100">
              {(() => {
                const done = session.topics.filter(t => t.status === 'complete').length
                const total = session.topics.length
                const pct = total > 0 ? Math.round((done / total) * 100) : 0
                return (
                  <>
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>Progress</span>
                      <span>{done}/{total} topics</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div className="bg-blue-500 h-2 rounded-full transition-all" style={{ width: `${pct}%` }} />
                    </div>
                    <p className="text-xs text-gray-400 mt-1 text-right">{pct}%</p>
                  </>
                )
              })()}
            </div>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {!selectedTopic || activeView === 'chat' ? (
            <GeneralChat session={session} voiceEnabled={voiceEnabled} />
          ) : (
            <>
              <div className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">Topic {selectedTopic.order}</p>
                    <h2 className="text-lg font-bold text-gray-900">{selectedTopic.title}</h2>
                    <p className="text-sm text-gray-500 mt-0.5">{selectedTopic.description}</p>
                  </div>
                  {selectedTopic.score !== null && (
                    <div className={`flex-shrink-0 text-center px-4 py-2 rounded-xl ${selectedTopic.passed ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
                      <p className="text-2xl font-bold">{selectedTopic.score}%</p>
                      <p className="text-xs font-medium">{selectedTopic.passed ? 'Passed' : 'Try Again'}</p>
                    </div>
                  )}
                </div>
                <div className="flex gap-1 mt-3">
                  <button
                    onClick={() => setActiveView('lesson')}
                    className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${activeView === 'lesson' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                  >
                    📖 Lesson
                  </button>
                  <button
                    onClick={() => setActiveView('quiz')}
                    className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${activeView === 'quiz' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                  >
                    ✏️ Quiz
                  </button>
                </div>
              </div>

              {activeView === 'lesson' && (
                <LessonChat session={session} topic={selectedTopic} voiceEnabled={voiceEnabled} onQuizReady={() => setActiveView('quiz')} />
              )}
              {activeView === 'quiz' && (
                <QuizChat session={session} topic={selectedTopic} voiceEnabled={voiceEnabled} onComplete={onRefresh} />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  )
}

// ─── Shared chat hook ─────────────────────────────────────────────────────────

function useChat(voiceEnabled: boolean) {
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [sending, setSending] = useState(false)
  const [alexSpeaking, setAlexSpeaking] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const addUser = (text: string) => setMessages(prev => [...prev, { role: 'user', text }])

  const addAlex = async (text: string, audio: string | null) => {
    setMessages(prev => [...prev, { role: 'alex', text }])
    if (audio && voiceEnabled) {
      setAlexSpeaking(true)
      await playAudio(audio)
      setAlexSpeaking(false)
    }
  }

  return { messages, setMessages, sending, setSending, alexSpeaking, addUser, addAlex, bottomRef }
}

// ─── Lesson Chat ──────────────────────────────────────────────────────────────

function LessonChat({
  session, topic, voiceEnabled, onQuizReady,
}: {
  session: Session
  topic: Topic
  voiceEnabled: boolean
  onQuizReady: () => void
}) {
  const { messages, setMessages, sending, setSending, alexSpeaking, addUser, addAlex, bottomRef } = useChat(voiceEnabled)
  const [quizPrompted, setQuizPrompted] = useState(false)
  const [error, setError] = useState('')
  const loadedTopicRef = useRef<number | null>(null)

  useEffect(() => {
    if (loadedTopicRef.current === topic.id) return
    loadedTopicRef.current = topic.id
    setMessages([])
    setQuizPrompted(false)
    loadOpening()
  }, [topic.id])

  const loadOpening = async () => {
    setSending(true)
    try {
      // Restore existing lesson history if returning to this topic
      const histRes = await apiFetch(`/api/guidance/sessions/${session.id}/messages/?topic=${topic.id}`)
      if (histRes.ok) {
        const history: { role: string; content: string }[] = await histRes.json()
        if (history.length > 0) {
          setMessages(history.map(m => ({ role: m.role as 'alex' | 'user', text: m.content })))
          setSending(false)
          return
        }
      }
      // No history — start the lesson fresh
      const res = await apiFetch(`/api/guidance/sessions/${session.id}/topics/${topic.id}/lesson/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: '', include_audio: voiceEnabled }),
      })
      if (res.ok) {
        const data = await res.json()
        await addAlex(data.response, data.audio)
        if (data.quiz_ready) setQuizPrompted(true)
      }
    } catch {}
    setSending(false)
  }

  const send = async (text: string) => {
    setError('')
    addUser(text)
    setSending(true)
    try {
      const res = await apiFetch(`/api/guidance/sessions/${session.id}/topics/${topic.id}/lesson/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, include_audio: voiceEnabled }),
      })
      if (!res.ok) { setError('Something went wrong.'); setSending(false); return }
      const data = await res.json()
      await addAlex(data.response, data.audio)
      if (data.quiz_ready && !quizPrompted) setQuizPrompted(true)
    } catch { setError('Network error.') }
    setSending(false)
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((m, i) => <ChatBubble key={i} msg={m} speaking={alexSpeaking && m.role === 'alex' && i === messages.length - 1} />)}
        {sending && <TypingIndicator />}
        {quizPrompted && (
          <div className="flex justify-center">
            <div className="bg-green-50 border border-green-200 rounded-xl px-5 py-4 text-center max-w-sm">
              <p className="text-green-700 font-semibold text-sm mb-2">🎉 Lesson complete! Ready for the quiz?</p>
              <button onClick={onQuizReady} className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-green-700">
                Start Quiz →
              </button>
            </div>
          </div>
        )}
        {error && <p className="text-center text-sm text-red-600">{error}</p>}
        <div ref={bottomRef} />
      </div>
      <div className="flex-shrink-0 bg-white border-t border-gray-200 px-6 py-4">
        <ChatInput onSend={send} disabled={sending} placeholder="Ask a question or respond to Alex..." voiceEnabled={voiceEnabled} />
      </div>
    </div>
  )
}

// ─── Quiz Chat ────────────────────────────────────────────────────────────────

function QuizChat({
  session, topic, voiceEnabled, onComplete,
}: {
  session: Session
  topic: Topic
  voiceEnabled: boolean
  onComplete: () => void
}) {
  const { messages, setMessages, sending, setSending, alexSpeaking, addUser, addAlex, bottomRef } = useChat(voiceEnabled)
  const [result, setResult] = useState<{ score: number; passed: boolean } | null>(null)
  const [error, setError] = useState('')
  const loadedTopicRef = useRef<number | null>(null)

  useEffect(() => {
    if (loadedTopicRef.current === topic.id) return
    loadedTopicRef.current = topic.id
    setMessages([])
    setResult(null)
    loadOpening()
  }, [topic.id])

  const loadOpening = async () => {
    setSending(true)
    try {
      // Restore existing quiz history if returning mid-quiz
      const histRes = await apiFetch(`/api/guidance/sessions/${session.id}/messages/?topic=${topic.id}`)
      if (histRes.ok) {
        const history: { role: string; content: string }[] = await histRes.json()
        if (history.length > 0) {
          setMessages(history.map(m => ({ role: m.role as 'alex' | 'user', text: m.content })))
          if (topic.score !== null) setResult({ score: topic.score, passed: topic.passed ?? false })
          setSending(false)
          return
        }
      }
      // No history — start the quiz fresh
      const res = await apiFetch(`/api/guidance/sessions/${session.id}/topics/${topic.id}/quiz/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: '', include_audio: voiceEnabled }),
      })
      if (res.ok) {
        const data = await res.json()
        await addAlex(data.response, data.audio)
      }
    } catch {}
    setSending(false)
  }

  const send = async (text: string) => {
    setError('')
    addUser(text)
    setSending(true)
    try {
      const res = await apiFetch(`/api/guidance/sessions/${session.id}/topics/${topic.id}/quiz/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, include_audio: voiceEnabled }),
      })
      if (!res.ok) { setError('Something went wrong.'); setSending(false); return }
      const data = await res.json()
      await addAlex(data.response, data.audio)
      if (data.quiz_complete) {
        setResult({ score: data.score, passed: data.passed })
        onComplete()
      }
    } catch { setError('Network error.') }
    setSending(false)
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((m, i) => <ChatBubble key={i} msg={m} speaking={alexSpeaking && m.role === 'alex' && i === messages.length - 1} />)}
        {sending && <TypingIndicator />}
        {result && (
          <div className="flex justify-center">
            <div className={`rounded-xl px-6 py-5 text-center max-w-sm border ${result.passed ? 'bg-green-50 border-green-200' : 'bg-orange-50 border-orange-200'}`}>
              <p className={`text-3xl font-bold mb-1 ${result.passed ? 'text-green-600' : 'text-orange-500'}`}>{result.score}%</p>
              <p className={`font-semibold text-sm ${result.passed ? 'text-green-700' : 'text-orange-600'}`}>
                {result.passed ? '🎉 Topic Passed! Next topic unlocked.' : 'Not quite — review the lesson and try again.'}
              </p>
            </div>
          </div>
        )}
        {error && <p className="text-center text-sm text-red-600">{error}</p>}
        <div ref={bottomRef} />
      </div>
      {!result && (
        <div className="flex-shrink-0 bg-white border-t border-gray-200 px-6 py-4">
          <ChatInput onSend={send} disabled={sending} placeholder="Type your answer..." voiceEnabled={voiceEnabled} />
        </div>
      )}
    </div>
  )
}

// ─── General Chat ─────────────────────────────────────────────────────────────

function GeneralChat({ session, voiceEnabled }: { session: Session; voiceEnabled: boolean }) {
  const { messages, setMessages, sending, setSending, alexSpeaking, addUser, addAlex, bottomRef } = useChat(voiceEnabled)
  const [error, setError] = useState('')
  const loadedRef = useRef(false)

  useEffect(() => {
    if (loadedRef.current) return
    loadedRef.current = true
    const loadHistory = async () => {
      const res = await apiFetch(`/api/guidance/sessions/${session.id}/messages/`).catch(() => null)
      if (res?.ok) {
        const history: { role: string; content: string }[] = await res.json()
        if (history.length > 0) {
          setMessages(history.map(m => ({ role: m.role as 'alex' | 'user', text: m.content })))
          return
        }
      }
      setMessages([{
        role: 'alex',
        text: `Hi! I'm Alex, your career coach. You're working towards "${session.goal}" — you're doing great! Ask me anything: career advice, questions about your roadmap, how to tackle a topic, anything at all. I'm here to help. 😊`,
      }])
    }
    loadHistory()
  }, [])

  const send = async (text: string) => {
    setError('')
    addUser(text)
    setSending(true)
    try {
      const res = await apiFetch(`/api/guidance/sessions/${session.id}/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, include_audio: voiceEnabled }),
      })
      if (!res.ok) { setError('Something went wrong.'); setSending(false); return }
      const data = await res.json()
      await addAlex(data.response, data.audio)
    } catch { setError('Network error.') }
    setSending(false)
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-4">
        <h2 className="text-lg font-bold text-gray-900">Ask Alex</h2>
        <p className="text-sm text-gray-500">Your personal career coach — ask anything</p>
      </div>
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((m, i) => <ChatBubble key={i} msg={m} speaking={alexSpeaking && m.role === 'alex' && i === messages.length - 1} />)}
        {sending && <TypingIndicator />}
        {error && <p className="text-center text-sm text-red-600">{error}</p>}
        <div ref={bottomRef} />
      </div>
      <div className="flex-shrink-0 bg-white border-t border-gray-200 px-6 py-4">
        <ChatInput onSend={send} disabled={sending} placeholder="Ask Alex anything..." voiceEnabled={voiceEnabled} />
      </div>
    </div>
  )
}
