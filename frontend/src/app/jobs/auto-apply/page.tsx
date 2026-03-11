'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

interface Job {
  id: string
  title: string
  company: string
  location: string
  description: string
  salary_range?: string
  job_type?: string
  experience_level?: string
  skills_required?: string[]
  source: string
  job_url?: string
}

interface MatchedJob {
  job: Job
  score: number
  selected: boolean
  tailoring: boolean
  tailored: boolean
  applying: boolean
  applied: boolean
  error?: string
}

const SOURCE_COLORS: Record<string, string> = {
  linkedin: 'bg-blue-100 text-blue-700',
  indeed: 'bg-indigo-100 text-indigo-700',
  glassdoor: 'bg-green-100 text-green-700',
  ziprecruiter: 'bg-sky-100 text-sky-700',
  adzuna: 'bg-orange-100 text-orange-700',
  remotive: 'bg-purple-100 text-purple-700',
  arbeitnow: 'bg-cyan-100 text-cyan-700',
  jobicy: 'bg-rose-100 text-rose-700',
  remoteok: 'bg-lime-100 text-lime-700',
  themuse: 'bg-violet-100 text-violet-700',
  brightermonday: 'bg-yellow-100 text-yellow-700',
  fuzu: 'bg-pink-100 text-pink-700',
  kenyajob: 'bg-teal-100 text-teal-700',
  myjobmag: 'bg-amber-100 text-amber-700',
}

function matchBadge(score: number) {
  if (score >= 80) return 'bg-green-100 text-green-700'
  if (score >= 60) return 'bg-blue-100 text-blue-700'
  if (score >= 40) return 'bg-yellow-100 text-yellow-700'
  return 'bg-gray-100 text-gray-500'
}

export default function AutoApplyPage() {
  return (
    <ProtectedRoute>
      <AutoApply />
    </ProtectedRoute>
  )
}

function AutoApply() {
  const [hasCv, setHasCv] = useState(false)
  const [loading, setLoading] = useState(true)
  const [matchedJobs, setMatchedJobs] = useState<MatchedJob[]>([])
  const [threshold, setThreshold] = useState(50)
  const [useTailoring, setUseTailoring] = useState(true)
  const [applying, setApplying] = useState(false)
  const [results, setResults] = useState<{ applied: number; failed: number; skipped: number } | null>(null)
  const [progress, setProgress] = useState<string>('')

  useEffect(() => {
    loadMatches()
  }, [])

  async function loadMatches() {
    setLoading(true)
    try {
      const [matchRes, jobsRes] = await Promise.all([
        apiFetch('/api/jobs/jobs/my_matches/'),
        apiFetch('/api/jobs/jobs/'),
      ])

      if (!matchRes.ok) {
        setHasCv(false)
        setLoading(false)
        return
      }

      const matchData = await matchRes.json()
      const jobsData = await jobsRes.json()

      setHasCv(matchData.has_cv || false)

      const jobs: Job[] = Array.isArray(jobsData) ? jobsData : (jobsData.results || [])
      const scores: Record<string, number> = matchData.matches || {}

      const matched: MatchedJob[] = jobs
        .filter(j => (scores[j.id] ?? 0) > 0)
        .sort((a, b) => (scores[b.id] ?? 0) - (scores[a.id] ?? 0))
        .map(j => ({
          job: j,
          score: scores[j.id] ?? 0,
          selected: (scores[j.id] ?? 0) >= 60,
          tailoring: false,
          tailored: false,
          applying: false,
          applied: false,
        }))

      setMatchedJobs(matched)
    } finally {
      setLoading(false)
    }
  }

  function toggleSelect(id: string) {
    setMatchedJobs(prev =>
      prev.map(m => m.job.id === id ? { ...m, selected: !m.selected } : m)
    )
  }

  function selectAll() {
    setMatchedJobs(prev => prev.map(m => ({ ...m, selected: m.score >= threshold })))
  }

  function deselectAll() {
    setMatchedJobs(prev => prev.map(m => ({ ...m, selected: false })))
  }

  const displayed = matchedJobs.filter(m => m.score >= threshold)
  const selectedCount = matchedJobs.filter(m => m.selected).length

  async function runAutoApply() {
    const toApply = matchedJobs.filter(m => m.selected && !m.applied)
    if (toApply.length === 0) return

    setApplying(true)
    setResults(null)
    let applied = 0, failed = 0, skipped = 0

    for (const item of toApply) {
      setProgress(`Processing ${item.job.title} at ${item.job.company}...`)

      // Mark as applying
      setMatchedJobs(prev =>
        prev.map(m => m.job.id === item.job.id ? { ...m, applying: true, error: undefined } : m)
      )

      let coverLetter = ''

      // Step 1: Tailor CV if enabled
      if (useTailoring) {
        setMatchedJobs(prev =>
          prev.map(m => m.job.id === item.job.id ? { ...m, tailoring: true } : m)
        )
        setProgress(`Tailoring CV for ${item.job.title}... (may take 1-3 min)`)

        try {
          const tailorRes = await apiFetch(`/api/jobs/jobs/${item.job.id}/tailor_cv/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
          })
          if (tailorRes.ok) {
            const d = await tailorRes.json()
            coverLetter = d.cover_letter || ''
            setMatchedJobs(prev =>
              prev.map(m => m.job.id === item.job.id ? { ...m, tailoring: false, tailored: true } : m)
            )
          } else {
            setMatchedJobs(prev =>
              prev.map(m => m.job.id === item.job.id ? { ...m, tailoring: false } : m)
            )
          }
        } catch {
          setMatchedJobs(prev =>
            prev.map(m => m.job.id === item.job.id ? { ...m, tailoring: false } : m)
          )
        }
      }

      // Step 2: Apply
      setProgress(`Applying to ${item.job.title} at ${item.job.company}...`)
      try {
        const applyRes = await apiFetch(`/api/jobs/jobs/${item.job.id}/apply/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cover_letter: coverLetter }),
        })

        if (applyRes.ok) {
          applied++
          setMatchedJobs(prev =>
            prev.map(m => m.job.id === item.job.id ? { ...m, applying: false, applied: true } : m)
          )
        } else {
          const d = await applyRes.json()
          const errMsg = d.detail || d.error || 'Failed'
          if (errMsg.includes('already applied')) {
            skipped++
            setMatchedJobs(prev =>
              prev.map(m => m.job.id === item.job.id ? { ...m, applying: false, applied: true, error: 'Already applied' } : m)
            )
          } else {
            failed++
            setMatchedJobs(prev =>
              prev.map(m => m.job.id === item.job.id ? { ...m, applying: false, error: errMsg } : m)
            )
          }
        }
      } catch (e) {
        failed++
        setMatchedJobs(prev =>
          prev.map(m => m.job.id === item.job.id ? { ...m, applying: false, error: 'Network error' } : m)
        )
      }
    }

    setProgress('')
    setResults({ applied, failed, skipped })
    setApplying(false)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading matches...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 py-3 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link href="/jobs" className="text-gray-500 hover:text-gray-900 text-sm">← Job Board</Link>
            <h1 className="text-xl font-bold text-gray-900">Auto Apply</h1>
          </div>
          <span className="text-sm text-gray-500">{selectedCount} job{selectedCount !== 1 ? 's' : ''} selected</span>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">

        {/* No CV warning */}
        {!hasCv && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-5 flex items-start gap-4">
            <span className="text-3xl">⚠️</span>
            <div>
              <p className="font-semibold text-yellow-800">No CV uploaded yet</p>
              <p className="text-sm text-yellow-700 mt-1">Upload your CV to enable AI job matching and auto-apply.</p>
              <Link href="/cv" className="mt-2 inline-block bg-yellow-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-yellow-700">
                Upload CV
              </Link>
            </div>
          </div>
        )}

        {/* Settings panel */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Auto Apply Settings</h2>
          <div className="grid sm:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Minimum Match Score: <span className="text-blue-600 font-bold">{threshold}%</span>
              </label>
              <input type="range" min={10} max={90} step={5} value={threshold}
                onChange={e => setThreshold(Number(e.target.value))}
                className="w-full accent-blue-600" />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>10% (show all)</span><span>90% (best matches)</span>
              </div>
            </div>
            <div className="space-y-3">
              <label className="flex items-start gap-3 cursor-pointer">
                <input type="checkbox" checked={useTailoring} onChange={e => setUseTailoring(e.target.checked)}
                  className="mt-0.5 accent-purple-600" />
                <div>
                  <p className="text-sm font-medium text-gray-800">AI Tailor CV for each job</p>
                  <p className="text-xs text-gray-500">Uses Ollama to customize your CV for each role. Slower (1-3 min/job) but higher quality.</p>
                </div>
              </label>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 mt-5">
            <button onClick={selectAll}
              className="text-sm text-blue-600 hover:underline">
              Select all above {threshold}% ({displayed.filter(m => !m.applied).length} jobs)
            </button>
            <button onClick={deselectAll} className="text-sm text-gray-500 hover:underline">Deselect all</button>
          </div>
        </div>

        {/* Results banner */}
        {results && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-5">
            <h3 className="font-semibold text-green-800 mb-2">Auto Apply Complete</h3>
            <div className="flex gap-6 text-sm">
              <span className="text-green-700"><strong>{results.applied}</strong> applied</span>
              <span className="text-yellow-700"><strong>{results.skipped}</strong> already applied</span>
              <span className="text-red-600"><strong>{results.failed}</strong> failed</span>
            </div>
          </div>
        )}

        {/* Progress */}
        {applying && progress && (
          <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-600 flex-shrink-0" />
            <p className="text-sm text-purple-700">{progress}</p>
          </div>
        )}

        {/* Job list */}
        {!hasCv ? null : matchedJobs.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <p className="text-4xl mb-3">🤖</p>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">No matches found yet</h3>
            <p className="text-sm text-gray-500 mb-4">Run the job fetcher first to get new jobs, then come back here.</p>
            <Link href="/jobs" className="bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700">
              Browse All Jobs
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-900">
                {displayed.length} matching job{displayed.length !== 1 ? 's' : ''} (score ≥ {threshold}%)
              </h2>
              <button
                onClick={runAutoApply}
                disabled={applying || selectedCount === 0 || !hasCv}
                className="bg-purple-600 text-white px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
              >
                {applying ? (
                  <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> Applying...</>
                ) : `Apply to ${selectedCount} selected`}
              </button>
            </div>

            {displayed.map(item => (
              <AutoApplyJobCard key={item.job.id} item={item} onToggle={() => toggleSelect(item.job.id)} />
            ))}

            {displayed.length > 0 && (
              <div className="text-center pt-2">
                <button
                  onClick={runAutoApply}
                  disabled={applying || selectedCount === 0 || !hasCv}
                  className="bg-purple-600 text-white px-8 py-3 rounded-xl text-sm font-semibold hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2 mx-auto"
                >
                  {applying ? (
                    <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> Applying...</>
                  ) : `Apply to ${selectedCount} selected job${selectedCount !== 1 ? 's' : ''}`}
                </button>
                {useTailoring && selectedCount > 0 && (
                  <p className="text-xs text-gray-500 mt-2">
                    With AI tailoring: estimated {selectedCount * 2}–{selectedCount * 3} minutes
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function AutoApplyJobCard({ item, onToggle }: { item: MatchedJob; onToggle: () => void }) {
  const { job, score, selected, tailoring, tailored, applying, applied, error } = item

  let statusBadge = null
  if (applied) statusBadge = <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">Applied ✓</span>
  else if (error) statusBadge = <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600 font-medium">{error}</span>
  else if (tailoring) statusBadge = <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 font-medium animate-pulse">Tailoring CV...</span>
  else if (applying) statusBadge = <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium animate-pulse">Applying...</span>
  else if (tailored) statusBadge = <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 font-medium">CV Tailored ✓</span>

  return (
    <div className={`bg-white rounded-xl border transition-all ${
      applied ? 'border-green-200 opacity-75' : selected ? 'border-blue-400 shadow-sm' : 'border-gray-200'
    }`}>
      <div className="p-4 flex items-start gap-4">
        {/* Checkbox */}
        <input type="checkbox" checked={selected} onChange={onToggle} disabled={applied || applying}
          className="mt-1 w-4 h-4 accent-blue-600 flex-shrink-0 cursor-pointer" />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${matchBadge(score)}`}>{score}% match</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${SOURCE_COLORS[job.source] || 'bg-gray-100 text-gray-600'}`}>
              {job.source}
            </span>
            {statusBadge}
          </div>
          <h3 className="text-sm font-semibold text-gray-900">{job.title}</h3>
          <p className="text-sm text-gray-600">{job.company} · {job.location}</p>
          {job.salary_range && <p className="text-xs text-green-600 font-medium mt-0.5">{job.salary_range}</p>}
          {(job.skills_required || []).length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {(job.skills_required || []).slice(0, 5).map((s, i) => (
                <span key={i} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{s}</span>
              ))}
            </div>
          )}
        </div>

        {/* View link */}
        {job.job_url && (
          <a href={job.job_url} target="_blank" rel="noopener noreferrer"
            className="flex-shrink-0 text-xs text-gray-400 hover:text-gray-700">↗</a>
        )}
      </div>
    </div>
  )
}
