'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

// ─── Types ────────────────────────────────────────────────────────────────────

interface InterviewQuestion {
  id: number
  phase: number
  order: number
  question_type: string
  question_text: string
  options: string[] | null
  correct_answer: string | null
  section: string | null
  answer?: {
    answer_text: string
    score: number
    feedback: string
    is_correct: boolean
    needs_review: boolean
  }
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
  questions: InterviewQuestion[]
  created_at: string
}

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
  const router = useRouter()
  const params = useParams()
  const sessionId = params.id as string

  const [session, setSession] = useState<InterviewSession | null>(null)
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
        const data = await res.json()
        setSession(data)
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

  // Route to correct phase UI
  if (session.status === 'phase1_test') {
    return (
      <Phase1Test
        session={session}
        onSessionUpdate={setSession}
        onPhaseComplete={() => router.push(`/interview/${sessionId}/review`)}
      />
    )
  }

  if (session.status === 'phase2_interview' || session.status === 'phase3_interview') {
    return (
      <ConversationalPhase
        session={session}
        onSessionUpdate={setSession}
        onPhaseComplete={() => router.push(`/interview/${sessionId}/review`)}
      />
    )
  }

  // Fallback for completed or unexpected statuses
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center max-w-md">
        <div className="text-5xl mb-4">
          {session.status === 'completed' ? '🎉' : '⏳'}
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          {session.status === 'completed' ? 'Interview Complete' : `Status: ${session.status}`}
        </h2>
        <p className="text-gray-600 mb-6">
          {session.status === 'completed'
            ? 'Your interview session is complete.'
            : 'This session is in an intermediate state.'}
        </p>
        <div className="flex gap-3 justify-center">
          {session.status === 'completed' && (
            <Link
              href={`/interview/${sessionId}/report`}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700"
            >
              View Final Report
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

// ─── Phase 1: Written Test ─────────────────────────────────────────────────────

function Phase1Test({
  session,
  onSessionUpdate,
  onPhaseComplete,
}: {
  session: InterviewSession
  onSessionUpdate: (s: InterviewSession) => void
  onPhaseComplete: () => void
}) {
  const phase1Questions = session.questions
    .filter((q) => q.phase === 1)
    .sort((a, b) => a.order - b.order)

  const [currentIndex, setCurrentIndex] = useState(() => {
    // Start at first unanswered question
    const firstUnanswered = phase1Questions.findIndex((q) => !q.answer)
    return firstUnanswered === -1 ? phase1Questions.length - 1 : firstUnanswered
  })

  const [selectedOption, setSelectedOption] = useState('')
  const [shortAnswer, setShortAnswer] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<{ correct: boolean; text: string } | null>(null)
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
      const res = await apiFetch(
        `/api/interview/sessions/${session.id}/answer/`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question_id: currentQuestion.id,
            answer_text: answerText,
          }),
        }
      )

      if (res.ok) {
        const data = await res.json()
        // Update session with new answer
        const updatedQuestions = session.questions.map((q) =>
          q.id === currentQuestion.id ? { ...q, answer: data.answer || data } : q
        )
        onSessionUpdate({ ...session, questions: updatedQuestions })

        const isCorrect = data.answer?.is_correct ?? data.is_correct ?? false
        const feedbackText =
          data.answer?.feedback || data.feedback || (isCorrect ? 'Great answer!' : 'Review the correct answer.')

        setFeedback({ correct: isCorrect, text: feedbackText })

        // Auto-advance after 1.5 seconds
        setTimeout(() => {
          setFeedback(null)
          setSelectedOption('')
          setShortAnswer('')
          if (currentIndex < totalQuestions - 1) {
            setCurrentIndex((i) => i + 1)
          }
        }, 1500)
      } else {
        const data = await res.json().catch(() => ({}))
        setError(data.error || data.detail || 'Failed to submit answer.')
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
      const res = await apiFetch(
        `/api/interview/sessions/${session.id}/complete-phase/`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phase: 1 }),
        }
      )
      if (res.ok) {
        onPhaseComplete()
      } else {
        const data = await res.json().catch(() => ({}))
        setError(data.error || data.detail || 'Failed to complete phase.')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setCompletingPhase(false)
    }
  }

  const optionLabels = ['A', 'B', 'C', 'D']

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold text-gray-900">Phase 1 — Written Test</h1>
              <p className="text-sm text-gray-500">
                Question {currentIndex + 1} of {totalQuestions}
              </p>
            </div>
            <div className="text-sm text-gray-500">
              {answeredCount}/{totalQuestions} answered
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-3 w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-purple-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(answeredCount / totalQuestions) * 100}%` }}
            />
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        {/* Feedback overlay */}
        {feedback && (
          <div
            className={`mb-6 p-4 rounded-xl border-2 flex items-start gap-3 ${
              feedback.correct
                ? 'bg-green-50 border-green-400'
                : 'bg-red-50 border-red-400'
            }`}
          >
            <span className="text-2xl">{feedback.correct ? '✅' : '❌'}</span>
            <div>
              <p className="font-semibold text-gray-900">
                {feedback.correct ? 'Correct!' : 'Incorrect'}
              </p>
              <p className="text-sm text-gray-700 mt-1">{feedback.text}</p>
            </div>
          </div>
        )}

        {/* Question card */}
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
                      disabled={!!currentQuestion.answer || !!feedback}
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
              <textarea
                value={currentQuestion.answer ? currentQuestion.answer.answer_text : shortAnswer}
                onChange={(e) => !currentQuestion.answer && setShortAnswer(e.target.value)}
                disabled={!!currentQuestion.answer || !!feedback}
                rows={4}
                placeholder="Type your answer here..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none disabled:bg-gray-50 disabled:text-gray-500"
              />
            )}

            {/* Already answered indicator */}
            {currentQuestion.answer && !feedback && (
              <div className={`mt-4 p-3 rounded-lg text-sm ${
                currentQuestion.answer.is_correct ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              }`}>
                {currentQuestion.answer.is_correct ? '✅ Answered correctly' : '❌ Answered incorrectly'}
                {currentQuestion.answer.feedback && (
                  <p className="mt-1 text-xs opacity-80">{currentQuestion.answer.feedback}</p>
                )}
              </div>
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
          {/* Previous */}
          {currentIndex > 0 && (
            <button
              onClick={() => {
                setCurrentIndex((i) => i - 1)
                setSelectedOption('')
                setShortAnswer('')
                setFeedback(null)
              }}
              className="px-4 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 text-sm font-medium"
            >
              ← Previous
            </button>
          )}

          {/* Submit answer (only when not answered yet) */}
          {currentQuestion && !currentQuestion.answer && !feedback && (
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

          {/* Next question navigation */}
          {currentQuestion?.answer && !feedback && currentIndex < totalQuestions - 1 && (
            <button
              onClick={() => {
                setCurrentIndex((i) => i + 1)
                setSelectedOption('')
                setShortAnswer('')
              }}
              className="flex-1 bg-purple-600 text-white py-3 rounded-xl font-semibold hover:bg-purple-700"
            >
              Next Question →
            </button>
          )}

          {/* Complete Phase 1 */}
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

        {/* Question navigation dots */}
        {totalQuestions > 1 && (
          <div className="flex justify-center gap-2 mt-6 flex-wrap">
            {phase1Questions.map((q, idx) => (
              <button
                key={q.id}
                onClick={() => {
                  setCurrentIndex(idx)
                  setSelectedOption('')
                  setShortAnswer('')
                  setFeedback(null)
                }}
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

interface ChatMessage {
  role: 'alex' | 'user'
  text: string
  audioBase64?: string
}

function ConversationalPhase({
  session,
  onSessionUpdate,
  onPhaseComplete,
}: {
  session: InterviewSession
  onSessionUpdate: (s: InterviewSession) => void
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
  const [alexReaction, setAlexReaction] = useState('')
  const [showReaction, setShowReaction] = useState(false)
  const [completingPhase, setCompletingPhase] = useState(false)
  const [error, setError] = useState('')

  const chatBottomRef = useRef<HTMLDivElement>(null)

  const currentQuestion = phaseQuestions[currentIndex]
  const totalQuestions = phaseQuestions.length
  const answeredCount = phaseQuestions.filter((q) => q.answer).length
  const allAnswered = answeredCount === totalQuestions

  // Build chat messages from answered questions
  const chatMessages: ChatMessage[] = []
  for (const q of phaseQuestions) {
    chatMessages.push({ role: 'alex', text: q.question_text })
    if (q.answer) {
      chatMessages.push({ role: 'user', text: q.answer.answer_text })
      if (q.answer.feedback) {
        chatMessages.push({ role: 'alex', text: q.answer.feedback })
      }
    }
  }
  // Show the current unanswered question if not already there
  if (currentQuestion && !currentQuestion.answer) {
    // Already included above via phase questions loop
  }

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages.length, showReaction])

  const playAudio = (base64: string) => {
    try {
      const audio = new Audio(`data:audio/mp3;base64,${base64}`)
      audio.play().catch(() => {})
    } catch {
      // Audio not supported / blocked — silently ignore
    }
  }

  const handleSubmitAnswer = async () => {
    if (!userAnswer.trim()) {
      setError('Please type your answer before submitting.')
      return
    }
    if (!currentQuestion) return

    setError('')
    setSubmitting(true)
    try {
      const res = await apiFetch(
        `/api/interview/sessions/${session.id}/answer/`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question_id: currentQuestion.id,
            answer_text: userAnswer.trim(),
          }),
        }
      )

      if (res.ok) {
        const data = await res.json()
        const answerData = data.answer || data

        // Play audio if TTS provided
        if (answerData.audio_base64 || data.audio_base64) {
          playAudio(answerData.audio_base64 || data.audio_base64)
        }

        // Update session
        const updatedQuestions = session.questions.map((q) =>
          q.id === currentQuestion.id ? { ...q, answer: answerData } : q
        )
        onSessionUpdate({ ...session, questions: updatedQuestions })

        // Show Alex's reaction
        const reaction = answerData.feedback || 'Thank you for that answer. Moving on...'
        setAlexReaction(reaction)
        setShowReaction(true)
        setUserAnswer('')

        // Advance to next question after a short delay
        setTimeout(() => {
          setShowReaction(false)
          setAlexReaction('')
          if (currentIndex < totalQuestions - 1) {
            setCurrentIndex((i) => i + 1)
          }
        }, 2500)
      } else {
        const data = await res.json().catch(() => ({}))
        setError(data.error || data.detail || 'Failed to submit answer.')
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
      const res = await apiFetch(
        `/api/interview/sessions/${session.id}/complete-phase/`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phase: phaseNum }),
        }
      )
      if (res.ok) {
        onPhaseComplete()
      } else {
        const data = await res.json().catch(() => ({}))
        setError(data.error || data.detail || 'Failed to complete phase.')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setCompletingPhase(false)
    }
  }

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

      {/* Chat messages */}
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

            {/* User's answer */}
            {q.answer && (
              <>
                <div className="flex justify-end mb-3">
                  <div className="bg-white border border-gray-200 rounded-2xl rounded-tr-none px-4 py-3 max-w-xl shadow-sm">
                    <p className="text-sm text-gray-800 leading-relaxed">{q.answer.answer_text}</p>
                  </div>
                </div>

                {/* Alex's feedback */}
                {q.answer.feedback && idx < currentIndex && (
                  <div className="flex items-start gap-3 mb-3">
                    <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white text-sm flex-shrink-0">
                      A
                    </div>
                    <div className="bg-purple-700 text-white rounded-2xl rounded-tl-none px-4 py-3 max-w-xl shadow-sm opacity-80">
                      <p className="text-sm leading-relaxed">{q.answer.feedback}</p>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        ))}

        {/* Alex's reaction to latest answer */}
        {showReaction && alexReaction && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white text-sm flex-shrink-0">
              A
            </div>
            <div className="bg-purple-700 text-white rounded-2xl rounded-tl-none px-4 py-3 max-w-xl shadow-sm">
              <p className="text-sm leading-relaxed">{alexReaction}</p>
              <div className="mt-2 flex gap-1">
                <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </main>

      {/* Input area */}
      <div className="bg-white border-t border-gray-200 sticky bottom-0">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm mb-3">
              {error}
            </div>
          )}

          {!allAnswered && !showReaction ? (
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
                disabled={submitting || showReaction}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none disabled:bg-gray-50"
              />
              <button
                onClick={handleSubmitAnswer}
                disabled={submitting || showReaction || !userAnswer.trim()}
                className="px-5 py-3 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 self-end"
              >
                {submitting ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                ) : (
                  '→'
                )}
              </button>
            </div>
          ) : allAnswered ? (
            <div className="flex items-center gap-4">
              <p className="text-gray-600 text-sm flex-1">
                All questions answered. Ready to move on to the review?
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
            <div className="text-sm text-gray-500 text-center py-2">Alex is responding...</div>
          )}
        </div>
      </div>
    </div>
  )
}
