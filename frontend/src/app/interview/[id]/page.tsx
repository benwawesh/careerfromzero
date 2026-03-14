'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch, streamFetch } from '@/lib/apiFetch'
import { useSentenceTTS } from '@/lib/sentenceTTS'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Question {
  id: number
  phase: number
  order: number
  question_type: string
  question_text: string
  options: string[] | null
  correct_answer: string | null
  ideal_answer_guide: string | null
  section: string | null
  answer?: {
    answer_text: string
    score: number
    feedback: string
    is_correct: boolean
    needs_review: boolean
  }
}

interface Session {
  id: string
  career_goal: string
  experience_level: string
  interview_type: string
  mode: string
  status: string
  phase1_score: number | null
  phase2_score: number | null
  phase3_score: number | null
  overall_score: number | null
  phase1_passed: boolean | null
  phase2_passed: boolean | null
  phase3_passed: boolean | null
  questions: Question[]
  created_at: string
}

type ChatMsg = { role: 'alex' | 'user'; text: string }

// ─── Helpers ──────────────────────────────────────────────────────────────────

// ─── Page wrapper ─────────────────────────────────────────────────────────────

export default function InterviewPage() {
  return (
    <ProtectedRoute>
      <InterviewSession />
    </ProtectedRoute>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

function InterviewSession() {
  const params = useParams()
  const sessionId = params.id as string

  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchSession()
  }, [sessionId])

  const fetchSession = async () => {
    setLoading(true)
    try {
      const res = await apiFetch(`/api/interview/sessions/${sessionId}/`)
      if (res.ok) {
        setSession(await res.json())
      } else if (res.status === 404) {
        setError('Interview session not found.')
      } else {
        setError('Failed to load interview session.')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto" />
          <p className="mt-4 text-gray-600">Loading your interview session...</p>
        </div>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <div className="text-5xl mb-4">😕</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Something went wrong</h2>
          <p className="text-gray-600 mb-6">{error || 'Session not found.'}</p>
          <Link href="/interview" className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700">
            Back to Interview Setup
          </Link>
        </div>
      </div>
    )
  }

  if (session.status === 'intro') {
    return <IntroChat session={session} onPhase1Ready={setSession} />
  }

  if (session.status === 'phase1_test') {
    return (
      <Phase1Test
        session={session}
        onSessionUpdate={setSession}
        onPhaseComplete={() => fetchSession()}
      />
    )
  }

  if (session.status === 'phase2_interview' || session.status === 'phase3_interview') {
    return (
      <ConversationalPhase
        session={session}
        onSessionUpdate={setSession}
        onPhaseComplete={() => fetchSession()}
      />
    )
  }

  // Completed / review / other statuses
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center max-w-md">
        <div className="text-5xl mb-4">
          {session.status === 'complete' ? '🎉' : '⏳'}
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          {session.status === 'complete' ? 'Interview Complete!' : `Status: ${session.status}`}
        </h2>
        <div className="flex gap-3 justify-center">
          {session.status === 'complete' && (
            <Link
              href={`/interview/${sessionId}/report`}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700"
            >
              View Final Report
            </Link>
          )}
          {(session.status.includes('review')) && (
            <Link
              href={`/interview/${sessionId}/review`}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700"
            >
              Go to Review
            </Link>
          )}
          <Link href="/interview" className="bg-gray-200 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-300">
            New Interview
          </Link>
        </div>
      </div>
    </div>
  )
}

// ─── Voice Input ──────────────────────────────────────────────────────────────

function getSupportedMimeType(): string {
  const types = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/mp4',
  ]
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

      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }

      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        if (chunksRef.current.length === 0) {
          setMicError('No audio recorded.')
          setTranscribing(false)
          return
        }
        const blob = new Blob(chunksRef.current, { type: actualMime || 'audio/webm' })
        const ext = mimeToExtension(actualMime)
        setTranscribing(true)
        try {
          const formData = new FormData()
          formData.append('audio', blob, `recording.${ext}`)
          const res = await apiFetch('/api/interview/transcribe/', { method: 'POST', body: formData })
          if (res.ok) {
            const data = await res.json()
            if (data.text?.trim()) {
              onTranscript(data.text.trim())
            } else {
              setMicError('No speech detected. Please try again.')
            }
          } else {
            const err = await res.json().catch(() => ({}))
            setMicError(err.error || 'Transcription failed. Please try again.')
          }
        } catch {
          setMicError('Network error during transcription.')
        }
        setTranscribing(false)
      }

      mr.start()
      setRecording(true)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : ''
      if (msg.includes('Permission') || msg.includes('NotAllowed') || msg.includes('denied')) {
        setMicError('Microphone access denied. Please allow it in your browser settings.')
      } else if (msg.includes('NotFound') || msg.includes('Requested device not found')) {
        setMicError('No microphone found. Please connect one and try again.')
      } else {
        setMicError('Could not start recording. Please check your microphone.')
      }
    }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        onClick={recording ? stopRecording : startRecording}
        disabled={disabled || transcribing}
        title={recording ? 'Stop recording' : 'Speak your answer'}
        className={`px-4 py-3 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all whitespace-nowrap ${
          recording
            ? 'bg-red-500 text-white animate-pulse hover:bg-red-600'
            : transcribing
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300'
        }`}
      >
        {transcribing ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-500" />
            <span className="hidden sm:inline">Transcribing...</span>
          </>
        ) : recording ? (
          <>⏹ <span className="hidden sm:inline">Stop</span></>
        ) : (
          <>🎤 <span className="hidden sm:inline">Speak</span></>
        )}
      </button>
      {micError && (
        <p className="text-xs text-red-500 max-w-[160px] leading-tight">{micError}</p>
      )}
    </div>
  )
}

// ─── Question Coach mini-chat ─────────────────────────────────────────────────

function QuestionCoach({
  session,
  question,
  onClose,
}: {
  session: Session
  question: Question
  onClose: () => void
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([
    {
      role: 'alex',
      text: question.answer?.feedback || "Let's go over your answer. What would you like to understand better?",
    },
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const { onToken, onStreamEnd, speakFull, stop } = useSentenceTTS()

  useEffect(() => {
    const initialText = question.answer?.feedback || "Let's go over your answer. What would you like to understand better?"
    speakFull(initialText)
    return () => stop() // cleanup cancels double-fire in React StrictMode
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  const send = async (text?: string) => {
    const msg = (text ?? input).trim()
    if (!msg || sending) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text: msg }])
    setSending(true)
    // Add empty alex message for streaming
    setMessages((prev) => [...prev, { role: 'alex', text: '' }])
    try {
      await streamFetch(
        `/api/interview/sessions/${session.id}/question-coach/stream/`,
        { question_id: question.id, message: msg },
        (token) => {
          onToken(token)
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last?.role === 'alex') updated[updated.length - 1] = { ...last, text: last.text + token }
            return updated
          })
        },
        async (data) => {
          const cleanText = data.full_text as string
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last?.role === 'alex') updated[updated.length - 1] = { ...last, text: cleanText }
            return updated
          })
          onStreamEnd()
        },
        (err) => console.error(err),
      )
    } catch {}
    setSending(false)
  }

  return (
    <div className="mt-4 border border-purple-200 rounded-xl bg-purple-50 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-purple-100 border-b border-purple-200">
        <div className="flex items-center gap-2 text-sm font-semibold text-purple-800">
          💬 Ask Alex about this question
        </div>
        <button onClick={onClose} className="text-purple-400 hover:text-purple-700 text-xl leading-none font-bold">×</button>
      </div>
      <div className="p-3 space-y-3 max-h-56 overflow-y-auto">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'items-start gap-2'}`}>
            {m.role === 'alex' && (
              <div className="w-6 h-6 bg-purple-600 rounded-full flex items-center justify-center text-white text-xs flex-shrink-0 mt-0.5">A</div>
            )}
            <div className={`rounded-xl px-3 py-2 text-sm max-w-xs leading-relaxed ${
              m.role === 'alex'
                ? 'bg-white text-gray-800 border border-purple-100'
                : 'bg-purple-600 text-white'
            }`}>
              {m.text}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex items-start gap-2">
            <div className="w-6 h-6 bg-purple-600 rounded-full flex items-center justify-center text-white text-xs flex-shrink-0">A</div>
            <div className="bg-white border border-purple-100 rounded-xl px-3 py-2 flex gap-1">
              <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="px-3 pb-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') send() }}
          placeholder="Ask Alex a question..."
          disabled={sending}
          className="flex-1 px-3 py-2 text-sm border border-purple-200 rounded-lg focus:ring-1 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-50"
        />
        <VoiceInput onTranscript={(t) => send(t)} disabled={sending} />
        <button
          onClick={() => send()}
          disabled={sending || !input.trim()}
          className="px-3 py-2 bg-purple-600 text-white rounded-lg text-sm font-semibold hover:bg-purple-700 disabled:opacity-50"
        >
          →
        </button>
      </div>
    </div>
  )
}

// ─── Intro Chat ────────────────────────────────────────────────────────────────

function IntroChat({
  session,
  onPhase1Ready,
}: {
  session: Session
  onPhase1Ready: (updatedSession: Session) => void
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [startingPhase1, setStartingPhase1] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const greetingFetched = useRef(false)
  const { onToken, onStreamEnd, speakFull } = useSentenceTTS()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, sending])

  useEffect(() => {
    if (greetingFetched.current) return
    greetingFetched.current = true
    fetchGreeting()
  }, [])

  const fetchGreeting = async () => {
    try {
      const res = await apiFetch(`/api/interview/sessions/${session.id}/intro/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: '' }),
      })
      if (res.ok) {
        const data = await res.json()
        setMessages([{ role: 'alex', text: data.response }])
        speakFull(data.response)
      }
    } catch {}
    setLoading(false)
  }

  const sendMessage = async (text: string) => {
    if (!text.trim() || sending || startingPhase1) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text }])
    setSending(true)
    // Add empty alex message for streaming
    setMessages((prev) => [...prev, { role: 'alex', text: '' }])
    try {
      let startPhase1 = false
      await streamFetch(
        `/api/interview/sessions/${session.id}/intro/stream/`,
        { message: text },
        (token) => {
          onToken(token)
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last?.role === 'alex') updated[updated.length - 1] = { ...last, text: last.text + token }
            return updated
          })
        },
        async (data) => {
          const cleanText = data.full_text as string
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last?.role === 'alex') updated[updated.length - 1] = { ...last, text: cleanText }
            return updated
          })
          onStreamEnd()
          if (data.start_phase1) startPhase1 = true
        },
        (err) => console.error(err),
      )
      if (startPhase1) {
        setSending(false)
        setStartingPhase1(true)
        const phase1Res = await apiFetch(`/api/interview/sessions/${session.id}/start-phase1/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
        if (phase1Res.ok) {
          onPhase1Ready(await phase1Res.json())
        }
        setStartingPhase1(false)
        return
      }
    } catch {}
    setSending(false)
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center text-xl">👤</div>
            <div>
              <p className="font-semibold text-gray-900">Alex — Interview Coach</p>
              <p className="text-xs text-gray-500">Introduction · {session.career_goal}</p>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-3xl w-full mx-auto px-4 sm:px-6 py-6 space-y-4 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto" />
              <p className="mt-3 text-sm text-gray-500">Alex is getting ready...</p>
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'items-start gap-3'}`}>
              {m.role === 'alex' && (
                <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white text-sm flex-shrink-0">A</div>
              )}
              <div className={`rounded-2xl px-4 py-3 max-w-xl shadow-sm text-sm leading-relaxed ${
                m.role === 'alex'
                  ? 'bg-purple-700 text-white rounded-tl-none'
                  : 'bg-white border border-gray-200 text-gray-800 rounded-tr-none'
              }`}>
                {m.text}
              </div>
            </div>
          ))
        )}

        {(sending || startingPhase1) && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white text-sm flex-shrink-0">A</div>
            <div className="bg-purple-700 rounded-2xl rounded-tl-none px-4 py-3 flex gap-1 items-center">
              <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}

        {startingPhase1 && (
          <div className="text-center py-2">
            <div className="inline-flex items-center gap-2 text-sm text-purple-700 bg-purple-50 px-4 py-2 rounded-full border border-purple-200">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-600" />
              Preparing your Phase 1 questions...
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      <div className="bg-white border-t border-gray-200 sticky bottom-0">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                  e.preventDefault()
                  sendMessage(input)
                }
              }}
              rows={2}
              placeholder="Type your reply... (Ctrl+Enter to send)"
              disabled={sending || startingPhase1 || loading}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none disabled:bg-gray-50"
            />
            <div className="flex flex-col gap-2 self-end">
              <VoiceInput
                onTranscript={(text) => sendMessage(text)}
                disabled={sending || startingPhase1 || loading}
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={sending || startingPhase1 || !input.trim() || loading}
                className="px-5 py-3 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Phase 1: Written Test ─────────────────────────────────────────────────────

function Phase1Test({
  session,
  onSessionUpdate,
  onPhaseComplete,
}: {
  session: Session
  onSessionUpdate: (s: Session) => void
  onPhaseComplete: () => void
}) {
  const phase1Questions = session.questions
    .filter((q) => q.phase === 1)
    .sort((a, b) => a.order - b.order)

  const [currentIndex, setCurrentIndex] = useState(() => {
    const firstUnanswered = phase1Questions.findIndex((q) => !q.answer)
    return firstUnanswered === -1 ? phase1Questions.length - 1 : firstUnanswered
  })
  const [selectedOption, setSelectedOption] = useState('')
  const [shortAnswer, setShortAnswer] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showCoach, setShowCoach] = useState(false)
  const [completingPhase, setCompletingPhase] = useState(false)
  const [error, setError] = useState('')

  const currentQuestion = phase1Questions[currentIndex]
  const totalQuestions = phase1Questions.length
  const answeredCount = phase1Questions.filter((q) => q.answer).length
  const allAnswered = answeredCount === totalQuestions

  const handleSubmitAnswer = async () => {
    const answerText =
      currentQuestion.question_type === 'short_answer' ? shortAnswer : selectedOption

    if (!answerText.trim()) {
      setError('Please provide an answer before continuing.')
      return
    }

    setError('')
    setSubmitting(true)
    try {
      const res = await apiFetch(`/api/interview/sessions/${session.id}/answer/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_id: currentQuestion.id, answer_text: answerText }),
      })

      if (res.ok) {
        const data = await res.json()
        const updatedQuestions = session.questions.map((q) =>
          q.id === currentQuestion.id
            ? {
                ...q,
                answer: {
                  answer_text: answerText,
                  score: data.score,
                  feedback: data.feedback,
                  is_correct: data.is_correct,
                  needs_review: data.needs_review,
                },
                correct_answer: data.correct_answer || q.correct_answer,
              }
            : q
        )
        onSessionUpdate({ ...session, questions: updatedQuestions })
        setSelectedOption('')
        setShortAnswer('')
        // Automatically open coaching for wrong answers
        if (!data.is_correct) setShowCoach(true)
      } else {
        const data = await res.json().catch(() => ({}))
        setError(data.error || 'Failed to submit answer.')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCompletePhase = async () => {
    setCompletingPhase(true)
    try {
      const res = await apiFetch(`/api/interview/sessions/${session.id}/complete-phase/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phase: 1 }),
      })
      if (res.ok) {
        onPhaseComplete()
      } else {
        const data = await res.json().catch(() => ({}))
        setError(data.error || 'Failed to complete phase.')
      }
    } catch {
      setError('Network error.')
    } finally {
      setCompletingPhase(false)
    }
  }

  const navigateTo = (idx: number) => {
    setCurrentIndex(idx)
    setSelectedOption('')
    setShortAnswer('')
    setShowCoach(false)
    setError('')
  }

  const optionLabels = ['A', 'B', 'C', 'D']

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold text-gray-900">Phase 1 — Written Test</h1>
              <p className="text-sm text-gray-500">
                Question {currentIndex + 1} of {totalQuestions}
              </p>
            </div>
            <div className="text-sm text-gray-500">{answeredCount}/{totalQuestions} answered</div>
          </div>
          <div className="mt-3 w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-purple-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(answeredCount / totalQuestions) * 100}%` }}
            />
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        {currentQuestion && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
            {currentQuestion.section && (
              <span className="text-xs font-medium text-purple-600 bg-purple-50 px-2 py-1 rounded mb-3 inline-block">
                {currentQuestion.section}
              </span>
            )}
            <p className="text-gray-900 font-medium text-lg leading-relaxed mb-6">
              {currentQuestion.question_text}
            </p>

            {/* Multiple choice / situational */}
            {(currentQuestion.question_type === 'multiple_choice' ||
              currentQuestion.question_type === 'situational') &&
              currentQuestion.options && (
                <div className="space-y-3">
                  {currentQuestion.options.map((option, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => !currentQuestion.answer && setSelectedOption(option)}
                      disabled={!!currentQuestion.answer}
                      className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all text-sm ${
                        currentQuestion.answer
                          ? currentQuestion.answer.answer_text === option
                            ? currentQuestion.answer.is_correct
                              ? 'border-green-500 bg-green-50 text-green-900'
                              : 'border-red-400 bg-red-50 text-red-900'
                            : option === currentQuestion.correct_answer
                            ? 'border-green-400 bg-green-50 text-green-800'
                            : 'border-gray-200 bg-gray-50 text-gray-500'
                          : selectedOption === option
                          ? 'border-purple-500 bg-purple-50 text-purple-900'
                          : 'border-gray-200 hover:border-purple-300 hover:bg-purple-50 text-gray-700'
                      }`}
                    >
                      <span className="font-semibold mr-3 text-gray-400">{optionLabels[idx]}.</span>
                      {option}
                    </button>
                  ))}
                </div>
              )}

            {/* Short answer */}
            {currentQuestion.question_type === 'short_answer' && (
              <div className="space-y-2">
                <textarea
                  value={currentQuestion.answer ? currentQuestion.answer.answer_text : shortAnswer}
                  onChange={(e) => !currentQuestion.answer && setShortAnswer(e.target.value)}
                  disabled={!!currentQuestion.answer}
                  rows={4}
                  placeholder="Type your answer here..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none disabled:bg-gray-50 disabled:text-gray-500"
                />
                {!currentQuestion.answer && (
                  <div className="flex justify-end">
                    <VoiceInput
                      onTranscript={(text) =>
                        setShortAnswer((prev) => (prev ? prev + ' ' + text : text))
                      }
                      disabled={submitting}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Answered result */}
            {currentQuestion.answer && (
              <div
                className={`mt-4 p-4 rounded-xl border-2 ${
                  currentQuestion.answer.is_correct
                    ? 'bg-green-50 border-green-300'
                    : 'bg-red-50 border-red-300'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xl">
                    {currentQuestion.answer.is_correct ? '✅' : '❌'}
                  </span>
                  <span className="font-semibold text-sm">
                    {currentQuestion.answer.is_correct ? 'Correct!' : 'Incorrect'} · Score:{' '}
                    {currentQuestion.answer.score}/10
                  </span>
                </div>
                <p className="text-sm text-gray-700">{currentQuestion.answer.feedback}</p>
              </div>
            )}

            {/* Ask Alex button / coaching panel */}
            {currentQuestion.answer && !showCoach && (
              <button
                onClick={() => setShowCoach(true)}
                className="mt-3 text-sm text-purple-600 hover:text-purple-800 font-medium flex items-center gap-1"
              >
                💬 Ask Alex about this question
              </button>
            )}
            {currentQuestion.answer && showCoach && (
              <QuestionCoach
                session={session}
                question={currentQuestion}
                onClose={() => setShowCoach(false)}
              />
            )}
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          {currentIndex > 0 && (
            <button
              onClick={() => navigateTo(currentIndex - 1)}
              className="px-4 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 text-sm font-medium"
            >
              ← Previous
            </button>
          )}

          {currentQuestion && !currentQuestion.answer && (
            <button
              onClick={handleSubmitAnswer}
              disabled={submitting}
              className="flex-1 bg-purple-600 text-white py-3 rounded-xl font-semibold hover:bg-purple-700 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  Evaluating...
                </>
              ) : (
                'Submit Answer →'
              )}
            </button>
          )}

          {currentQuestion?.answer && currentIndex < totalQuestions - 1 && (
            <button
              onClick={() => navigateTo(currentIndex + 1)}
              className="flex-1 bg-purple-600 text-white py-3 rounded-xl font-semibold hover:bg-purple-700"
            >
              Next Question →
            </button>
          )}

          {allAnswered && (
            <button
              onClick={handleCompletePhase}
              disabled={completingPhase}
              className="flex-1 bg-green-600 text-white py-3 rounded-xl font-semibold hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {completingPhase ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  Processing...
                </>
              ) : (
                'Complete Phase 1 ✓'
              )}
            </button>
          )}
        </div>

        {/* Navigation dots */}
        {totalQuestions > 1 && (
          <div className="flex justify-center gap-2 mt-6 flex-wrap">
            {phase1Questions.map((q, idx) => (
              <button
                key={q.id}
                onClick={() => navigateTo(idx)}
                className={`w-8 h-8 rounded-full text-xs font-semibold transition-all ${
                  idx === currentIndex
                    ? 'bg-purple-600 text-white ring-2 ring-purple-300'
                    : q.answer
                    ? q.answer.is_correct
                      ? 'bg-green-100 text-green-700 hover:bg-green-200'
                      : 'bg-red-100 text-red-700 hover:bg-red-200'
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                }`}
              >
                {idx + 1}
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

// ─── Phase 2 & 3: Conversational Interview ─────────────────────────────────────

function ConversationalPhase({
  session,
  onSessionUpdate,
  onPhaseComplete,
}: {
  session: Session
  onSessionUpdate: (s: Session) => void
  onPhaseComplete: () => void
}) {
  const phaseNum = session.status === 'phase2_interview' ? 2 : 3
  const phaseQuestions = session.questions
    .filter((q) => q.phase === phaseNum)
    .sort((a, b) => a.order - b.order)

  const [currentIndex, setCurrentIndex] = useState(() => {
    const firstUnanswered = phaseQuestions.findIndex((q) => !q.answer)
    return firstUnanswered === -1 ? 0 : firstUnanswered
  })
  const [userAnswer, setUserAnswer] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showCoach, setShowCoach] = useState(false)
  const [completingPhase, setCompletingPhase] = useState(false)
  const [error, setError] = useState('')
  const chatBottomRef = useRef<HTMLDivElement>(null)
  const { speakFull } = useSentenceTTS()

  const currentQuestion = phaseQuestions[currentIndex]
  const totalQuestions = phaseQuestions.length
  const answeredCount = phaseQuestions.filter((q) => q.answer).length
  const allAnswered = answeredCount === totalQuestions

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [answeredCount, currentIndex])

  const handleSubmitAnswer = async () => {
    if (!userAnswer.trim()) {
      setError('Please provide an answer before submitting.')
      return
    }
    if (!currentQuestion) return
    setError('')
    setSubmitting(true)
    try {
      const res = await apiFetch(`/api/interview/sessions/${session.id}/answer/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: currentQuestion.id,
          answer_text: userAnswer.trim(),
        }),
      })
      if (res.ok) {
        const data = await res.json()
        const updatedQuestions = session.questions.map((q) =>
          q.id === currentQuestion.id
            ? {
                ...q,
                answer: {
                  answer_text: userAnswer.trim(),
                  score: data.score,
                  feedback: data.feedback,
                  is_correct: data.is_correct,
                  needs_review: data.needs_review,
                },
              }
            : q
        )
        onSessionUpdate({ ...session, questions: updatedQuestions })
        setUserAnswer('')
        if (data.feedback) speakFull(data.feedback as string)
      } else {
        const data = await res.json().catch(() => ({}))
        setError(data.error || 'Failed to submit answer.')
      }
    } catch {
      setError('Network error.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCompletePhase = async () => {
    setCompletingPhase(true)
    try {
      const res = await apiFetch(`/api/interview/sessions/${session.id}/complete-phase/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phase: phaseNum }),
      })
      if (res.ok) {
        onPhaseComplete()
      } else {
        const data = await res.json().catch(() => ({}))
        setError(data.error || 'Failed to complete phase.')
      }
    } catch {
      setError('Network error.')
    } finally {
      setCompletingPhase(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center text-xl">
                👤
              </div>
              <div>
                <p className="font-semibold text-gray-900">Alex — Interview Coach</p>
                <p className="text-xs text-gray-500">
                  Phase {phaseNum} · Question {currentIndex + 1} of {totalQuestions}
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-500">{answeredCount}/{totalQuestions} answered</div>
              <div className="w-24 bg-gray-200 rounded-full h-1.5 mt-1">
                <div
                  className="bg-purple-600 h-1.5 rounded-full transition-all"
                  style={{ width: `${(answeredCount / totalQuestions) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-3xl w-full mx-auto px-4 sm:px-6 py-6 space-y-4 overflow-y-auto">
        {phaseQuestions.map((q, idx) => (
          <div key={q.id}>
            {/* Alex's question */}
            <div className="flex items-start gap-3 mb-3">
              <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white text-sm flex-shrink-0">
                A
              </div>
              <div className="bg-purple-700 text-white rounded-2xl rounded-tl-none px-4 py-3 max-w-xl shadow-sm">
                <p className="text-sm leading-relaxed">{q.question_text}</p>
              </div>
            </div>

            {/* User's answer + Alex's feedback */}
            {q.answer && (
              <>
                <div className="flex justify-end mb-3">
                  <div className="bg-white border border-gray-200 rounded-2xl rounded-tr-none px-4 py-3 max-w-xl shadow-sm">
                    <p className="text-sm text-gray-800 leading-relaxed">{q.answer.answer_text}</p>
                  </div>
                </div>

                {q.answer.feedback && (
                  <div className="flex items-start gap-3 mb-2">
                    <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white text-sm flex-shrink-0">
                      A
                    </div>
                    <div className="bg-purple-700 text-white rounded-2xl rounded-tl-none px-4 py-3 max-w-xl shadow-sm opacity-90">
                      <p className="text-sm leading-relaxed">{q.answer.feedback}</p>
                    </div>
                  </div>
                )}

                {/* Coaching for current answered question */}
                {idx === currentIndex && (
                  <div className="ml-11">
                    {!showCoach ? (
                      <button
                        onClick={() => setShowCoach(true)}
                        className="text-sm text-purple-600 hover:text-purple-800 font-medium flex items-center gap-1"
                      >
                        💬 Ask Alex about this answer
                      </button>
                    ) : (
                      <QuestionCoach
                        session={session}
                        question={q}
                        onClose={() => setShowCoach(false)}
                      />
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        ))}

        {/* Next question button */}
        {currentQuestion?.answer && currentIndex < totalQuestions - 1 && (
          <div className="flex justify-end">
            <button
              onClick={() => {
                setCurrentIndex((i) => i + 1)
                setShowCoach(false)
                setError('')
              }}
              className="bg-purple-600 text-white px-5 py-2 rounded-xl text-sm font-semibold hover:bg-purple-700"
            >
              Next Question →
            </button>
          </div>
        )}

        <div ref={chatBottomRef} />
      </main>

      <div className="bg-white border-t border-gray-200 sticky bottom-0">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm mb-3">
              {error}
            </div>
          )}

          {!allAnswered && !currentQuestion?.answer ? (
            <div className="flex gap-3">
              <textarea
                value={userAnswer}
                onChange={(e) => setUserAnswer(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault()
                    handleSubmitAnswer()
                  }
                }}
                rows={3}
                placeholder="Type your answer... (Ctrl+Enter to submit)"
                disabled={submitting}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none disabled:bg-gray-50"
              />
              <div className="flex flex-col gap-2 self-end">
                <VoiceInput
                  onTranscript={(text) =>
                    setUserAnswer((prev) => (prev ? prev + ' ' + text : text))
                  }
                  disabled={submitting}
                />
                <button
                  onClick={handleSubmitAnswer}
                  disabled={submitting || !userAnswer.trim()}
                  className="px-5 py-3 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  ) : (
                    '→'
                  )}
                </button>
              </div>
            </div>
          ) : allAnswered ? (
            <div className="flex items-center gap-4">
              <p className="text-gray-600 text-sm flex-1">
                All questions answered. Ready for the review?
              </p>
              <button
                onClick={handleCompletePhase}
                disabled={completingPhase}
                className="bg-green-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-green-700 disabled:opacity-60 flex items-center gap-2"
              >
                {completingPhase ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                    Processing...
                  </>
                ) : (
                  'Complete Phase ✓'
                )}
              </button>
            </div>
          ) : (
            <p className="text-sm text-gray-500 text-center py-2">
              Answer submitted — click &quot;Next Question →&quot; to continue.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
