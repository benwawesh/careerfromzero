'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch, streamFetch } from '@/lib/apiFetch'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ReviewMessage {
  role: 'alex' | 'user'
  text: string
}

interface ReviewData {
  phase: number
  score: number | null
  passed: boolean | null
  opening_message: string
  audio_base64?: string
  next_phase?: string | null
  session_status?: string
}

interface InterviewSession {
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
  questions: any[]
  created_at: string
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ReviewPage() {
  return (
    <ProtectedRoute>
      <ReviewSession />
    </ProtectedRoute>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

function ReviewSession() {
  const router = useRouter()
  const params = useParams()
  const sessionId = params.id as string

  const [session, setSession] = useState<InterviewSession | null>(null)
  const [reviewData, setReviewData] = useState<ReviewData | null>(null)
  const [messages, setMessages] = useState<ReviewMessage[]>([])
  const [userInput, setUserInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [reviewComplete, setReviewComplete] = useState(false)

  const chatBottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    initializeReview()
  }, [sessionId])

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const playAudio = (base64: string) => {
    try {
      const audio = new Audio(`data:audio/mp3;base64,${base64}`)
      audio.play().catch(() => {})
    } catch {
      // Silently ignore audio errors
    }
  }

  const initializeReview = async () => {
    setLoading(true)
    try {
      // Load session
      const sessionRes = await apiFetch(`/api/interview/sessions/${sessionId}/`)
      if (!sessionRes.ok) {
        setError('Failed to load session.')
        setLoading(false)
        return
      }
      const sessionData: InterviewSession = await sessionRes.json()
      setSession(sessionData)

      // Start review
      const reviewRes = await apiFetch(`/api/interview/sessions/${sessionId}/review/`)
      if (reviewRes.ok) {
        const data: ReviewData = await reviewRes.json()
        setReviewData(data)
        setMessages([{ role: 'alex', text: data.opening_message }])

        if (data.audio_base64) {
          playAudio(data.audio_base64)
        }
      } else {
        setError('Failed to start review.')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async () => {
    if (!userInput.trim() || sending) return

    const text = userInput.trim()
    setUserInput('')
    setSending(true)

    // Add user message immediately
    setMessages((prev) => [...prev, { role: 'user', text }])
    // Add empty alex message for streaming
    setMessages((prev) => [...prev, { role: 'alex', text: '' }])

    try {
      await streamFetch(
        `/api/interview/sessions/${sessionId}/review/stream/`,
        { message: text },
        (token) => {
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
          if (data.audio) playAudio(data.audio as string)
        },
        (err) => {
          setError(err)
          // Remove the empty alex placeholder on error
          setMessages((prev) => prev.slice(0, -1))
          setUserInput(text)
        },
      )
    } catch {
      setError('Network error. Please try again.')
      setMessages((prev) => prev.slice(0, -2))
      setUserInput(text)
    } finally {
      setSending(false)
      inputRef.current?.focus()
    }
  }

  const handleDone = async () => {
    setMessages((prev) => [...prev, { role: 'user', text: "I'm done with this review." }])
    setSending(true)
    setMessages((prev) => [...prev, { role: 'alex', text: '' }])
    try {
      await streamFetch(
        `/api/interview/sessions/${sessionId}/review/stream/`,
        { message: "I'm ready to move on." },
        (token) => {
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
          if (data.audio) playAudio(data.audio as string)
        },
        () => {
          // Non-critical on error
        },
      )
    } catch {
      // Non-critical
    } finally {
      setSending(false)
      setReviewComplete(true)
    }
  }

  const handleRepeatPhase = async () => {
    try {
      const res = await apiFetch(`/api/interview/sessions/${sessionId}/repeat-phase/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      if (res.ok) {
        const data = await res.json()
        router.push(`/interview/${data.id || sessionId}`)
      } else {
        // Fallback: just go back to interview page
        router.push(`/interview/${sessionId}`)
      }
    } catch {
      router.push(`/interview/${sessionId}`)
    }
  }

  const getNextPhaseLabel = () => {
    if (!session) return null
    if (session.status === 'review_phase1' || session.phase1_passed) {
      return 'Move to Phase 2'
    }
    if (session.status === 'review_phase2' || session.phase2_passed) {
      return 'Move to Phase 3'
    }
    return 'View Final Report'
  }

  const getNextPhaseAction = () => {
    if (!session) return () => {}
    const isFinalReview =
      session.status === 'review_phase3' ||
      session.status === 'completed' ||
      (session.phase1_passed && session.phase2_passed)

    if (isFinalReview) {
      return () => router.push(`/interview/${sessionId}/report`)
    }
    return () => router.push(`/interview/${sessionId}`)
  }

  const getCurrentPhase = () => {
    if (!session) return 1
    if (session.status?.includes('phase1') || session.status === 'review_phase1') return 1
    if (session.status?.includes('phase2') || session.status === 'review_phase2') return 2
    return 3
  }

  const getPhaseScore = () => {
    const phase = getCurrentPhase()
    if (phase === 1) return session?.phase1_score
    if (phase === 2) return session?.phase2_score
    return session?.phase3_score
  }

  const getPhasePassed = () => {
    const phase = getCurrentPhase()
    if (phase === 1) return session?.phase1_passed
    if (phase === 2) return session?.phase2_passed
    return session?.phase3_passed
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto" />
          <p className="mt-4 text-gray-600">Alex is reviewing your performance...</p>
        </div>
      </div>
    )
  }

  if (error && messages.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <div className="text-5xl mb-4">😕</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Something went wrong</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <Link href={`/interview/${sessionId}`} className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700">
            Back to Interview
          </Link>
        </div>
      </div>
    )
  }

  const phaseNum = getCurrentPhase()
  const score = getPhaseScore()
  const passed = getPhasePassed()
  const isLastPhase =
    session?.status === 'review_phase3' ||
    session?.status === 'completed' ||
    reviewData?.next_phase === null

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center text-xl">
                👤
              </div>
              <div>
                <p className="font-semibold text-gray-900">Alex — Interview Coach</p>
                <p className="text-xs text-gray-500">Phase {phaseNum} Review</p>
              </div>
            </div>

            {/* Score badge */}
            {score !== null && score !== undefined && (
              <div className={`px-4 py-2 rounded-full text-sm font-semibold ${
                passed
                  ? 'bg-green-100 text-green-700'
                  : 'bg-yellow-100 text-yellow-700'
              }`}>
                {Math.round(score)}%
                {passed !== null && (
                  <span className="ml-1">{passed ? '✅ Passed' : '⚠️ Below Pass Mark'}</span>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Chat messages */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 sm:px-6 py-6 space-y-4 overflow-y-auto">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'alex' ? 'justify-start' : 'justify-end'}`}>
            {msg.role === 'alex' && (
              <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white text-sm flex-shrink-0 mr-3 mt-1">
                A
              </div>
            )}
            <div
              className={`max-w-xl px-4 py-3 rounded-2xl shadow-sm text-sm leading-relaxed ${
                msg.role === 'alex'
                  ? 'bg-purple-700 text-white rounded-tl-none'
                  : 'bg-white border border-gray-200 text-gray-800 rounded-tr-none'
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white text-sm flex-shrink-0 mr-3 mt-1">
              A
            </div>
            <div className="bg-purple-700 text-white rounded-2xl rounded-tl-none px-4 py-3 flex gap-1 items-center">
              <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}

        {/* Choice panel after review complete */}
        {reviewComplete && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 mt-4">
            <h3 className="font-semibold text-gray-900 mb-2">What would you like to do next?</h3>
            <p className="text-sm text-gray-500 mb-4">
              {passed === false
                ? 'You can repeat this phase to improve your score, or continue to the next phase.'
                : 'Great work! Ready to move on?'}
            </p>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleRepeatPhase}
                className="px-5 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium"
              >
                Repeat Phase {phaseNum}
              </button>
              <button
                onClick={getNextPhaseAction()}
                className="px-5 py-2.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium"
              >
                {isLastPhase ? 'View Final Report' : `Move to Phase ${phaseNum + 1}`} →
              </button>
            </div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </main>

      {/* Input area */}
      {!reviewComplete && (
        <div className="bg-white border-t border-gray-200 sticky bottom-0">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm mb-3">
                {error}
              </div>
            )}
            <div className="flex gap-3">
              <textarea
                ref={inputRef}
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault()
                    handleSend()
                  }
                }}
                rows={2}
                placeholder="Reply to Alex... (Ctrl+Enter to send)"
                disabled={sending}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none disabled:bg-gray-50"
              />
              <div className="flex flex-col gap-2 self-end">
                <button
                  onClick={handleSend}
                  disabled={sending || !userInput.trim()}
                  className="px-4 py-2.5 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  Send
                </button>
                <button
                  onClick={handleDone}
                  disabled={sending}
                  className="px-4 py-2 border border-gray-300 text-gray-600 rounded-xl text-xs hover:bg-gray-50 disabled:opacity-50"
                >
                  I'm Done
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
