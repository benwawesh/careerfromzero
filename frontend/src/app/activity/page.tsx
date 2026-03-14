'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { apiFetch } from '@/lib/apiFetch'
import TokenBalance from '@/components/TokenBalance'

// ── Types ────────────────────────────────────────────────────────────────────

interface InterviewSession {
  id: string
  career_goal: string
  experience_level: string
  interview_type: string
  status: string
  phase1_score: number | null
  phase2_score: number | null
  phase3_score: number | null
  overall_score: number | null
  phase1_passed: boolean | null
  phase2_passed: boolean | null
  phase3_passed: boolean | null
  created_at: string
  updated_at: string
}

interface GuidanceTopic {
  id: number
  order: number
  title: string
  status: string
  score: number | null
  passed: boolean | null
}

interface GuidanceSession {
  id: string
  goal: string
  status: string
  current_level: string
  topics: GuidanceTopic[]
  created_at: string
  updated_at: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const INTERVIEW_STATUS_LABELS: Record<string, string> = {
  intro: 'Intro',
  phase1_test: 'Phase 1 — Written Test',
  phase1_review: 'Phase 1 — Review',
  phase2_interview: 'Phase 2 — HR Interview',
  phase2_review: 'Phase 2 — Review',
  phase3_interview: 'Phase 3 — Technical',
  phase3_review: 'Phase 3 — Review',
  complete: 'Complete',
}

function isInterviewActive(s: InterviewSession) {
  return s.status !== 'complete'
}

function isGuidanceActive(s: GuidanceSession) {
  return s.status === 'onboarding' || s.status === 'active'
}

function guidanceProgress(s: GuidanceSession) {
  if (!s.topics.length) return 0
  const done = s.topics.filter(t => t.status === 'complete').length
  return Math.round((done / s.topics.length) * 100)
}

function currentGuidanceTopic(s: GuidanceSession) {
  return s.topics.find(t => t.status === 'in_progress') ?? s.topics[0] ?? null
}

function avgScore(sessions: InterviewSession[]) {
  const scores = sessions
    .map(s => s.overall_score)
    .filter((v): v is number => v !== null)
  if (!scores.length) return null
  return (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function ScorePill({ score, passed }: { score: number | null; passed: boolean | null }) {
  if (score === null) return <span className="text-gray-400 text-sm">—</span>
  const color = passed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
  return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${color}`}>{score}/10</span>
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ActivityPage() {
  const { user, isAuthenticated, loading, logout } = useAuth()
  const router = useRouter()
  const [interviews, setInterviews] = useState<InterviewSession[]>([])
  const [guidance, setGuidance] = useState<GuidanceSession[]>([])
  const [fetching, setFetching] = useState(true)

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login')
  }, [isAuthenticated, loading, router])

  useEffect(() => {
    if (!isAuthenticated) return
    Promise.all([
      apiFetch('/api/interview/sessions/').then(r => r.json()),
      apiFetch('/api/guidance/sessions/').then(r => r.json()),
    ]).then(([iv, gd]) => {
      setInterviews(Array.isArray(iv) ? iv : [])
      setGuidance(Array.isArray(gd) ? gd : [])
    }).catch(() => {}).finally(() => setFetching(false))
  }, [isAuthenticated])

  if (loading || fetching) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    )
  }

  if (!isAuthenticated || !user) return null

  const activeInterviews = interviews.filter(isInterviewActive)
  const pastInterviews = interviews.filter(s => !isInterviewActive(s))
  const activeGuidance = guidance.filter(isGuidanceActive)
  const pastGuidance = guidance.filter(s => s.status === 'complete')

  const totalTopicsDone = guidance.reduce(
    (acc, s) => acc + s.topics.filter(t => t.status === 'complete').length, 0
  )
  const avg = avgScore(interviews)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Career AI System</h1>
            <p className="text-sm text-gray-600">Welcome back, {user.first_name}!</p>
          </div>
          <div className="flex items-center space-x-4">
            <TokenBalance />
            <Link href="/dashboard" className="text-gray-600 hover:text-gray-900 text-sm">Dashboard</Link>
            <Link href="/profile" className="text-gray-600 hover:text-gray-900 text-sm">Profile</Link>
            <button onClick={logout} className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm">
              Sign Out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

        {/* Page title */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900">My Activity</h2>
          <p className="text-gray-500 text-sm mt-1">Your interviews, coaching sessions, and progress — all in one place.</p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Interviews Taken', value: interviews.length, color: 'text-purple-600' },
            { label: 'Avg Interview Score', value: avg ? `${avg}/10` : '—', color: 'text-blue-600' },
            { label: 'Career Goals Active', value: activeGuidance.length, color: 'text-pink-600' },
            { label: 'Topics Completed', value: totalTopicsDone, color: 'text-green-600' },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-xl shadow-sm p-5 text-center">
              <div className={`text-3xl font-bold ${s.color}`}>{s.value}</div>
              <div className="text-gray-500 text-sm mt-1">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Continue where you left off */}
        {(activeInterviews.length > 0 || activeGuidance.length > 0) && (
          <section>
            <h3 className="text-lg font-semibold text-gray-800 mb-3">Continue where you left off</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {activeInterviews.map(s => (
                <div key={s.id} className="bg-white rounded-xl shadow-sm p-5 flex items-center justify-between border-l-4 border-purple-500">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-purple-600 text-lg">🎤</span>
                      <span className="font-semibold text-gray-900 truncate max-w-xs">{s.career_goal}</span>
                    </div>
                    <div className="text-sm text-gray-500">
                      {INTERVIEW_STATUS_LABELS[s.status] ?? s.status} · {s.interview_type} · {fmtDate(s.updated_at)}
                    </div>
                  </div>
                  <Link
                    href={`/interview/${s.id}`}
                    className="ml-4 shrink-0 bg-purple-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-purple-700"
                  >
                    Continue →
                  </Link>
                </div>
              ))}

              {activeGuidance.map(s => {
                const topic = currentGuidanceTopic(s)
                const pct = guidanceProgress(s)
                const done = s.topics.filter(t => t.status === 'complete').length
                return (
                  <div key={s.id} className="bg-white rounded-xl shadow-sm p-5 border-l-4 border-pink-500">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-pink-600 text-lg">🎯</span>
                        <span className="font-semibold text-gray-900 truncate max-w-xs">{s.goal}</span>
                      </div>
                      <Link
                        href={`/ai/career-guidance/${s.id}`}
                        className="shrink-0 bg-pink-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-pink-700"
                      >
                        Continue →
                      </Link>
                    </div>
                    {topic && (
                      <div className="text-sm text-gray-500 mb-2">
                        Current: {topic.title}
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-100 rounded-full h-2">
                        <div className="bg-pink-500 h-2 rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-gray-500 shrink-0">{done}/{s.topics.length} topics</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        )}

        {/* Past Interviews */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-800">Interview History</h3>
            <Link href="/interview" className="text-sm text-purple-600 hover:underline">+ New Interview</Link>
          </div>
          {pastInterviews.length === 0 && activeInterviews.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm p-8 text-center text-gray-400">
              No interviews yet.{' '}
              <Link href="/interview" className="text-purple-600 hover:underline">Start your first one →</Link>
            </div>
          ) : pastInterviews.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm p-6 text-center text-gray-400 text-sm">
              No completed interviews yet — finish your current one to see results here.
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
                  <tr>
                    <th className="text-left px-5 py-3">Role</th>
                    <th className="text-left px-5 py-3 hidden md:table-cell">Type</th>
                    <th className="text-center px-3 py-3">Ph 1</th>
                    <th className="text-center px-3 py-3">Ph 2</th>
                    <th className="text-center px-3 py-3">Ph 3</th>
                    <th className="text-center px-3 py-3">Overall</th>
                    <th className="text-left px-5 py-3 hidden md:table-cell">Date</th>
                    <th className="px-5 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {pastInterviews.map(s => (
                    <tr key={s.id} className="hover:bg-gray-50">
                      <td className="px-5 py-3 font-medium text-gray-900 max-w-[200px] truncate">{s.career_goal}</td>
                      <td className="px-5 py-3 text-gray-500 hidden md:table-cell capitalize">{s.interview_type}</td>
                      <td className="px-3 py-3 text-center"><ScorePill score={s.phase1_score} passed={s.phase1_passed} /></td>
                      <td className="px-3 py-3 text-center"><ScorePill score={s.phase2_score} passed={s.phase2_passed} /></td>
                      <td className="px-3 py-3 text-center"><ScorePill score={s.phase3_score} passed={s.phase3_passed} /></td>
                      <td className="px-3 py-3 text-center">
                        {s.overall_score !== null
                          ? <span className="text-sm font-bold text-gray-800">{s.overall_score}/10</span>
                          : <span className="text-gray-400">—</span>}
                      </td>
                      <td className="px-5 py-3 text-gray-400 hidden md:table-cell">{fmtDate(s.created_at)}</td>
                      <td className="px-5 py-3">
                        <Link href={`/interview/${s.id}`} className="text-purple-600 hover:underline text-xs">
                          View report
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Career Coaching Sessions */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-800">Career Coaching</h3>
            <Link href="/ai/career-guidance" className="text-sm text-pink-600 hover:underline">+ New Goal</Link>
          </div>
          {guidance.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm p-8 text-center text-gray-400">
              No coaching sessions yet.{' '}
              <Link href="/ai/career-guidance" className="text-pink-600 hover:underline">Start your career journey →</Link>
            </div>
          ) : (
            <div className="space-y-3">
              {guidance.map(s => {
                const done = s.topics.filter(t => t.status === 'complete').length
                const pct = guidanceProgress(s)
                const avgTopicScore = s.topics
                  .map(t => t.score)
                  .filter((v): v is number => v !== null)
                const topicAvg = avgTopicScore.length
                  ? (avgTopicScore.reduce((a, b) => a + b, 0) / avgTopicScore.length).toFixed(0)
                  : null

                return (
                  <div key={s.id} className="bg-white rounded-xl shadow-sm p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-pink-600">🎯</span>
                          <span className="font-semibold text-gray-900 truncate">{s.goal}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ml-1 ${
                            s.status === 'complete' ? 'bg-green-100 text-green-700'
                            : s.status === 'active' ? 'bg-blue-100 text-blue-700'
                            : 'bg-yellow-100 text-yellow-700'
                          }`}>
                            {s.status === 'onboarding' ? 'Onboarding' : s.status === 'active' ? 'In Progress' : 'Complete'}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 mt-2">
                          <div className="flex-1 bg-gray-100 rounded-full h-2">
                            <div className="bg-pink-500 h-2 rounded-full transition-all" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-xs text-gray-500 shrink-0">{done}/{s.topics.length} topics</span>
                          {topicAvg && (
                            <span className="text-xs text-gray-500 shrink-0">Avg score: {topicAvg}%</span>
                          )}
                        </div>

                        {/* Topic chips */}
                        {s.topics.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {s.topics.map(t => (
                              <span key={t.id} className={`text-xs px-2 py-0.5 rounded-full ${
                                t.status === 'complete'
                                  ? t.passed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                  : t.status === 'in_progress'
                                  ? 'bg-blue-100 text-blue-700'
                                  : 'bg-gray-100 text-gray-500'
                              }`}>
                                {t.title}
                                {t.score !== null && ` · ${t.score}%`}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <Link
                        href={`/ai/career-guidance/${s.id}`}
                        className={`shrink-0 px-4 py-2 rounded-lg text-sm font-medium ${
                          s.status === 'complete'
                            ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            : 'bg-pink-600 text-white hover:bg-pink-700'
                        }`}
                      >
                        {s.status === 'complete' ? 'Review' : 'Continue →'}
                      </Link>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>

      </main>
    </div>
  )
}
