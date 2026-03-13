'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

interface GuidanceSession {
  id: string
  goal: string
  current_level: string
  status: string
  topics: { id: number; title: string; status: string; score: number | null }[]
  created_at: string
}

export default function CareerGuidancePage() {
  return (
    <ProtectedRoute>
      <CareerGuidanceList />
    </ProtectedRoute>
  )
}

function CareerGuidanceList() {
  const router = useRouter()
  const [sessions, setSessions] = useState<GuidanceSession[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [goal, setGoal] = useState('')
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    apiFetch('/api/guidance/sessions/')
      .then(r => r.ok ? r.json() : [])
      .then(data => { setSessions(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const createSession = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!goal.trim()) return
    setError('')
    setCreating(true)
    try {
      const res = await apiFetch('/api/guidance/sessions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: goal.trim() }),
      })
      if (res.ok) {
        const session = await res.json()
        router.push(`/ai/career-guidance/${session.id}`)
      } else {
        const d = await res.json().catch(() => ({}))
        setError(d.error || 'Failed to create session.')
        setCreating(false)
      }
    } catch {
      setError('Network error. Please try again.')
      setCreating(false)
    }
  }

  const levelLabel: Record<string, string> = {
    beginner: 'Beginner',
    some_experience: 'Some Experience',
    intermediate: 'Intermediate',
    experienced: 'Experienced',
  }

  const statusBadge = (s: string) => {
    if (s === 'onboarding') return <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-medium">Setting Up</span>
    if (s === 'active') return <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">In Progress</span>
    if (s === 'complete') return <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">Complete</span>
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <Link href="/dashboard" className="text-gray-500 hover:text-gray-900 text-sm">← Dashboard</Link>
            <h1 className="text-xl font-bold text-gray-900 mt-1">Career Coach</h1>
            <p className="text-sm text-gray-500">Your personal AI career trainer</p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-xl font-semibold hover:bg-blue-700 text-sm"
          >
            + New Goal
          </button>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {showForm && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-bold text-gray-900 mb-1">What's your career goal?</h2>
            <p className="text-sm text-gray-500 mb-4">Be specific — e.g. "Become a software engineer", "Learn Python for data science", "Get promoted to senior manager"</p>
            <form onSubmit={createSession} className="space-y-3">
              <textarea
                value={goal}
                onChange={e => setGoal(e.target.value)}
                placeholder="e.g. I want to become a full-stack web developer from scratch"
                rows={3}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm resize-none"
                disabled={creating}
              />
              {error && <p className="text-sm text-red-600">{error}</p>}
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={creating || !goal.trim()}
                  className="flex-1 bg-blue-600 text-white py-3 rounded-xl font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {creating ? 'Starting...' : 'Start Coaching →'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowForm(false); setGoal(''); setError('') }}
                  className="px-4 py-3 border border-gray-300 rounded-xl text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {loading ? (
          <div className="text-center py-16 text-gray-400">Loading...</div>
        ) : sessions.length === 0 && !showForm ? (
          <div className="text-center py-16">
            <div className="text-5xl mb-4">🎯</div>
            <h2 className="text-xl font-bold text-gray-800 mb-2">No coaching sessions yet</h2>
            <p className="text-gray-500 mb-6">Tell Alex your career goal and get a personalised roadmap + daily lessons.</p>
            <button
              onClick={() => setShowForm(true)}
              className="bg-blue-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-blue-700"
            >
              Start Your First Session
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {sessions.map(s => {
              const completed = s.topics.filter(t => t.status === 'complete').length
              const total = s.topics.length
              const pct = total > 0 ? Math.round((completed / total) * 100) : 0
              return (
                <Link
                  key={s.id}
                  href={`/ai/career-guidance/${s.id}`}
                  className="block bg-white rounded-2xl shadow-sm border border-gray-200 p-5 hover:border-blue-300 hover:shadow-md transition-all"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-lg">🎯</span>
                        <h3 className="font-bold text-gray-900 truncate">{s.goal}</h3>
                      </div>
                      <div className="flex items-center gap-3 text-sm text-gray-500 flex-wrap">
                        {s.current_level && <span>{levelLabel[s.current_level] || s.current_level}</span>}
                        {total > 0 && <span>{completed}/{total} topics</span>}
                        <span>{new Date(s.created_at).toLocaleDateString()}</span>
                      </div>
                      {total > 0 && (
                        <div className="mt-3">
                          <div className="w-full bg-gray-100 rounded-full h-1.5">
                            <div className="bg-blue-500 h-1.5 rounded-full transition-all" style={{ width: `${pct}%` }} />
                          </div>
                          <p className="text-xs text-gray-400 mt-1">{pct}% complete</p>
                        </div>
                      )}
                    </div>
                    <div className="flex-shrink-0">{statusBadge(s.status)}</div>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
