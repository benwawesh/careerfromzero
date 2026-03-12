'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ScoreBreakdown {
  communication: number
  technical_knowledge: number
  problem_solving: number
  culture_fit: number
}

interface ReportData {
  session_id: string
  career_goal: string
  experience_level: string
  interview_type: string
  overall_score: number
  phase1_score: number | null
  phase2_score: number | null
  phase3_score: number | null
  phase1_passed: boolean | null
  phase2_passed: boolean | null
  phase3_passed: boolean | null
  score_breakdown: ScoreBreakdown
  strengths: string[]
  areas_to_improve: string[]
  encouragement: string
  certificate_worthy: boolean
  created_at: string
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ReportPage() {
  return (
    <ProtectedRoute>
      <FinalReport />
    </ProtectedRoute>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

function FinalReport() {
  const params = useParams()
  const sessionId = params.id as string

  const [report, setReport] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchReport()
  }, [sessionId])

  const fetchReport = async () => {
    setLoading(true)
    try {
      const res = await apiFetch(`/api/interview/sessions/${sessionId}/report/`)
      if (res.ok) {
        const data = await res.json()
        setReport(data)
      } else if (res.status === 404) {
        setError('Report not found. The interview may not be complete yet.')
      } else {
        setError('Failed to load report.')
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
          <p className="mt-4 text-gray-600">Loading your interview report...</p>
        </div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <div className="text-5xl mb-4">📋</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Report Unavailable</h2>
          <p className="text-gray-600 mb-6">{error || 'Something went wrong.'}</p>
          <div className="flex gap-3 justify-center">
            <Link href={`/interview/${sessionId}`} className="bg-purple-600 text-white px-5 py-2.5 rounded-lg hover:bg-purple-700 text-sm font-medium">
              Continue Interview
            </Link>
            <Link href="/dashboard" className="bg-gray-200 text-gray-700 px-5 py-2.5 rounded-lg hover:bg-gray-300 text-sm font-medium">
              Dashboard
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const score = Math.round(report.overall_score)
  const scoreColor =
    score >= 70 ? 'text-green-600' : score >= 60 ? 'text-yellow-500' : 'text-red-500'
  const scoreBg =
    score >= 70 ? 'bg-green-50 border-green-200' : score >= 60 ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200'
  const scoreLabel =
    score >= 70 ? 'Excellent' : score >= 60 ? 'Good' : score >= 50 ? 'Fair' : 'Needs Improvement'

  const handleDownloadReport = () => {
    alert('PDF download coming soon!')
  }

  const breakdownCategories = [
    { key: 'communication', label: 'Communication', icon: '💬', value: report.score_breakdown?.communication ?? 0 },
    { key: 'technical_knowledge', label: 'Technical Knowledge', icon: '🔧', value: report.score_breakdown?.technical_knowledge ?? 0 },
    { key: 'problem_solving', label: 'Problem Solving', icon: '🧩', value: report.score_breakdown?.problem_solving ?? 0 },
    { key: 'culture_fit', label: 'Culture Fit', icon: '🤝', value: report.score_breakdown?.culture_fit ?? 0 },
  ]

  const phaseScores = [
    { label: 'Phase 1', score: report.phase1_score, passed: report.phase1_passed },
    { label: 'Phase 2', score: report.phase2_score, passed: report.phase2_passed },
    { label: 'Phase 3', score: report.phase3_score, passed: report.phase3_passed },
  ].filter((p) => p.score !== null)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Interview Complete ✓</h1>
            <p className="text-sm text-gray-500">{report.career_goal}</p>
          </div>
          <Link href="/dashboard" className="text-gray-500 hover:text-gray-700 text-sm font-medium">
            Dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

        {/* Certificate banner */}
        {report.certificate_worthy && (
          <div className="bg-gradient-to-r from-yellow-400 to-orange-400 rounded-xl p-5 text-white shadow-md">
            <div className="flex items-center gap-4">
              <div className="text-4xl">🏆</div>
              <div>
                <p className="font-bold text-lg">Interview Ready Certificate</p>
                <p className="text-yellow-100 text-sm">
                  {report.career_goal} · {formatExperienceLevel(report.experience_level)}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Overall score */}
        <div className={`bg-white rounded-xl shadow-sm border-2 ${scoreBg} p-8 text-center`}>
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">Overall Score</p>
          <div className={`text-7xl font-bold ${scoreColor} mb-3`}>{score}%</div>
          <div className={`inline-flex items-center px-4 py-1.5 rounded-full text-sm font-semibold ${
            score >= 70 ? 'bg-green-100 text-green-700' : score >= 60 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-600'
          }`}>
            {scoreLabel}
          </div>

          {/* Phase scores */}
          {phaseScores.length > 0 && (
            <div className="flex justify-center gap-3 mt-5 flex-wrap">
              {phaseScores.map((p) => (
                <span
                  key={p.label}
                  className={`px-4 py-1.5 rounded-full text-sm font-medium ${
                    p.passed
                      ? 'bg-green-100 text-green-700'
                      : 'bg-red-100 text-red-600'
                  }`}
                >
                  {p.label}: {p.score !== null ? `${Math.round(p.score)}%` : 'N/A'}
                  {p.passed !== null && (p.passed ? ' ✅' : ' ❌')}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Score breakdown */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-5">Score Breakdown</h2>
          <div className="space-y-4">
            {breakdownCategories.map((cat) => {
              const val = Math.round(cat.value)
              const barColor =
                val >= 70 ? 'bg-green-500' : val >= 50 ? 'bg-yellow-400' : 'bg-red-400'
              return (
                <div key={cat.key}>
                  <div className="flex justify-between items-center mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-base">{cat.icon}</span>
                      <span className="text-sm font-medium text-gray-800">{cat.label}</span>
                    </div>
                    <span className={`text-sm font-semibold ${
                      val >= 70 ? 'text-green-600' : val >= 50 ? 'text-yellow-600' : 'text-red-500'
                    }`}>
                      {val}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2.5">
                    <div
                      className={`${barColor} h-2.5 rounded-full transition-all duration-700`}
                      style={{ width: `${Math.min(val, 100)}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Strengths & Areas to Improve */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Strengths */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <span className="text-green-500">✅</span> Strengths
            </h2>
            {report.strengths && report.strengths.length > 0 ? (
              <ul className="space-y-2">
                {report.strengths.map((s, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-green-500 mt-0.5 flex-shrink-0">•</span>
                    {s}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-400">No strengths recorded yet.</p>
            )}
          </div>

          {/* Areas to Improve */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <span className="text-yellow-500">⚠️</span> Areas to Improve
            </h2>
            {report.areas_to_improve && report.areas_to_improve.length > 0 ? (
              <ul className="space-y-2">
                {report.areas_to_improve.map((area, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-yellow-500 mt-0.5 flex-shrink-0">•</span>
                    {area}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-400">No improvement areas recorded.</p>
            )}
          </div>
        </div>

        {/* Alex's encouragement */}
        {report.encouragement && (
          <div className="bg-purple-50 border border-purple-100 rounded-xl p-5">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center text-white font-semibold flex-shrink-0">
                A
              </div>
              <div>
                <p className="text-sm font-semibold text-purple-900 mb-1">Alex says:</p>
                <p className="text-sm text-purple-800 leading-relaxed">{report.encouragement}</p>
              </div>
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <div className="flex flex-wrap gap-3 justify-center">
            <button
              onClick={handleDownloadReport}
              className="flex items-center gap-2 px-5 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium"
            >
              📥 Download Report PDF
            </button>
            <Link
              href="/interview"
              className="flex items-center gap-2 px-5 py-2.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium"
            >
              🔁 Take Another Interview
            </Link>
            <Link
              href="/dashboard"
              className="flex items-center gap-2 px-5 py-2.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm font-medium"
            >
              🏠 Dashboard
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatExperienceLevel(level: string): string {
  const map: Record<string, string> = {
    junior: 'Junior / Entry Level',
    mid: 'Mid Level',
    senior: 'Senior',
    manager: 'Managerial / Team Lead',
    director: 'Director / Executive',
  }
  return map[level] || level
}
