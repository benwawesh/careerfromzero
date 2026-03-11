'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Job {
  id: string
  title: string
  company: string
  location: string
  description: string
  salary_min?: number
  salary_max?: number
  salary_range?: string
  job_type?: string
  experience_level?: string
  skills_required?: string[]
  source: string
  job_url?: string
  company_logo_url?: string
  posted_date?: string
  created_at: string
  view_count?: number
  application_count?: number
}

interface MatchScoreData {
  matches: Record<string, number>
  has_cv: boolean
  cv_skills: string[]
}

interface CustomizationResult {
  job_id: string
  job_title: string
  company: string
  status: 'success' | 'failed'
  data?: {
    tailored_summary: string
    key_skills: string[]
    changes_made: string[]
    cover_letter: string
  }
  error?: string
}

interface BulkResult {
  batch_id: string
  status: 'completed' | 'processing'
  total_jobs: number
  successful_jobs: number
  failed_jobs: number
  results: CustomizationResult[]
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

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

const SOURCE_NAMES: Record<string, string> = {
  linkedin: 'LinkedIn', indeed: 'Indeed', glassdoor: 'Glassdoor',
  ziprecruiter: 'ZipRecruiter', adzuna: 'Adzuna',
  remotive: 'Remotive', arbeitnow: 'Arbeitnow', jobicy: 'Jobicy',
  remoteok: 'RemoteOK', themuse: 'The Muse',
  brightermonday: 'BrighterMonday', fuzu: 'Fuzu',
  kenyajob: 'KenyaJob', myjobmag: 'MyJobMag',
}

function matchBadge(score: number) {
  if (score >= 80) return 'bg-green-100 text-green-700 border-green-200'
  if (score >= 60) return 'bg-blue-100 text-blue-700 border-blue-200'
  if (score >= 40) return 'bg-yellow-100 text-yellow-700 border-yellow-200'
  return 'bg-gray-100 text-gray-500 border-gray-200'
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
}

// ─── Page ─────────────────────────────────────────────────────────────────────

function AIMatchesContent() {
  return (
    <ProtectedRoute>
      <AIMatchesBoard />
    </ProtectedRoute>
  )
}

export default function AIMatchesPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    }>
      <AIMatchesContent />
    </Suspense>
  )
}

function AIMatchesBoard() {
  const searchParams = useSearchParams()
  const cvIdFromUrl = searchParams.get('cv_id')
  
  const [jobs, setJobs] = useState<Job[]>([])
  const [matchScores, setMatchScores] = useState<Record<string, number>>({})
  const [selectedJobIds, setSelectedJobIds] = useState<Set<string>>(new Set())
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set())
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set())
  const [hasCv, setHasCv] = useState(false)
  const [loadingMatches, setLoadingMatches] = useState(false)
  
  const [loading, setLoading] = useState(true)
  const [customizing, setCustomizing] = useState(false)
  const [bulkResult, setBulkResult] = useState<BulkResult | null>(null)
  
  const [search, setSearch] = useState('')
  const [jobTypeFilter, setJobTypeFilter] = useState('')
  const [locationFilter, setLocationFilter] = useState('')

  useEffect(() => {
    fetchJobs()
    fetchMatchScores()
    fetchSavedIds()
    fetchAppliedIds()
  }, [])

  async function fetchJobs() {
    setLoading(true)
    try {
      const r = await apiFetch('/api/jobs/jobs/')
      if (r.ok) {
        const d = await r.json()
        setJobs(Array.isArray(d) ? d : (d.results || []))
      }
    } finally {
      setLoading(false)
    }
  }

  async function fetchMatchScores() {
    try {
      const r = await apiFetch('/api/jobs/jobs/my_matches/')
      if (r.ok) {
        const d: MatchScoreData = await r.json()
        setMatchScores(d.matches || {})
        setHasCv(d.has_cv || false)
      }
    } catch { /* non-critical */ }
  }

  async function fetchSavedIds() {
    try {
      const r = await apiFetch('/api/jobs/jobs/saved_ids/')
      if (r.ok) { 
        const d = await r.json(); 
        setSavedIds(new Set(d.saved_ids || [])) 
      }
    } catch { /* non-critical */ }
  }

  async function fetchAppliedIds() {
    try {
      const r = await apiFetch('/api/jobs/jobs/applied_ids/')
      if (r.ok) { 
        const d = await r.json(); 
        setAppliedIds(new Set(d.applied_ids || [])) 
      }
    } catch { /* non-critical */ }
  }

  function toggleJobSelection(jobId: string) {
    setSelectedJobIds(prev => {
      const next = new Set(prev)
      if (next.has(jobId)) {
        next.delete(jobId)
      } else {
        next.add(jobId)
      }
      return next
    })
  }

  function selectTopJobs(count: number) {
    const sortedJobs = [...jobs]
      .filter(j => matchScores[j.id] > 0)
      .sort((a, b) => (matchScores[b.id] ?? 0) - (matchScores[a.id] ?? 0))
    
    setSelectedJobIds(new Set(sortedJobs.slice(0, count).map(j => j.id)))
  }

  function clearSelection() {
    setSelectedJobIds(new Set())
  }

  async function handleBulkCustomize() {
    if (selectedJobIds.size === 0) {
      alert('Please select at least one job')
      return
    }

    setCustomizing(true)
    setBulkResult(null)

    try {
      const r = await apiFetch('/api/jobs/jobs/bulk_tailor_cvs/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_ids: Array.from(selectedJobIds),
        }),
      })

      if (r.ok) {
        const d: BulkResult = await r.json()
        setBulkResult(d)
      } else {
        const d = await r.json()
        alert(d.error || 'Bulk customization failed')
      }
    } catch (e) {
      alert('Network error during bulk customization')
    } finally {
      setCustomizing(false)
    }
  }

  const displayed = useCallback(() => {
    let list = jobs.filter(j => (matchScores[j.id] ?? 0) > 0)
    
    if (search) {
      const q = search.toLowerCase()
      list = list.filter(j =>
        j.title.toLowerCase().includes(q) ||
        j.company.toLowerCase().includes(q) ||
        j.description.toLowerCase().includes(q) ||
        (j.skills_required || []).some(s => s.toLowerCase().includes(q))
      )
    }

    if (locationFilter) {
      list = list.filter(j => (j.location || '').toLowerCase().includes(locationFilter.toLowerCase()))
    }

    if (jobTypeFilter) {
      list = list.filter(j => j.job_type === jobTypeFilter)
    }

    return [...list].sort((a, b) => (matchScores[b.id] ?? 0) - (matchScores[a.id] ?? 0))
  }, [jobs, matchScores, search, locationFilter, jobTypeFilter])()

  // Redirect if no cv_id provided
  if (!cvIdFromUrl && !loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md text-center">
          <div className="text-5xl mb-4">📋</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Select a CV First</h2>
          <p className="text-gray-600 mb-6">
            Please choose a CV to see AI-curated job matches
          </p>
          <Link
            href="/jobs/ai-curate"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700"
          >
            Go to AI Curation
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Header ── */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link href="/jobs/ai-curate" className="text-gray-500 hover:text-gray-900 text-sm">← AI Curation</Link>
            <h1 className="text-xl font-bold text-gray-900">AI-Curated Jobs</h1>
          </div>
          <div className="flex items-center gap-2">
            {cvIdFromUrl && (
              <span className="text-sm text-blue-600">✓ CV Selected</span>
            )}
          </div>
        </div>
      </header>

      {/* ── Controls Bar ── */}
      <div className="bg-white border-b border-gray-200 py-4">
        <div className="max-w-7xl mx-auto px-4 flex flex-wrap gap-4 items-center justify-between">
          <div className="flex-1 min-w-64">
            <input
              type="text"
              placeholder="Search matched jobs..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <div className="flex gap-2">
            <select
              value={jobTypeFilter}
              onChange={e => setJobTypeFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">All Types</option>
              <option value="full_time">Full-time</option>
              <option value="remote">Remote</option>
              <option value="contract">Contract</option>
            </select>
            
            <input
              type="text"
              placeholder="Location..."
              value={locationFilter}
              onChange={e => setLocationFilter(e.target.value)}
              className="w-36 px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
        </div>
      </div>

      {/* ── Selection Controls ── */}
      <div className="bg-blue-50 border-b border-blue-200 py-3">
        <div className="max-w-7xl mx-auto px-4 flex flex-wrap gap-3 items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-700">
              Selected: <strong className="text-blue-700">{selectedJobIds.size}</strong> jobs
            </span>
            
            <button
              onClick={() => selectTopJobs(10)}
              disabled={loading || displayed.length < 10}
              className="px-3 py-1.5 bg-white border border-blue-300 text-blue-700 text-sm rounded hover:bg-blue-50 disabled:opacity-50"
            >
              Select Top 10
            </button>
            
            <button
              onClick={() => selectTopJobs(20)}
              disabled={loading || displayed.length < 20}
              className="px-3 py-1.5 bg-white border border-blue-300 text-blue-700 text-sm rounded hover:bg-blue-50 disabled:opacity-50"
            >
              Select Top 20
            </button>
            
            <button
              onClick={() => selectTopJobs(50)}
              disabled={loading || displayed.length < 50}
              className="px-3 py-1.5 bg-white border border-blue-300 text-blue-700 text-sm rounded hover:bg-blue-50 disabled:opacity-50"
            >
              Select Top 50
            </button>
            
            <button
              onClick={clearSelection}
              disabled={selectedJobIds.size === 0}
              className="px-3 py-1.5 bg-white border border-gray-300 text-gray-600 text-sm rounded hover:bg-gray-50 disabled:opacity-50"
            >
              Clear Selection
            </button>
          </div>
          
          <button
            onClick={handleBulkCustomize}
            disabled={customizing || selectedJobIds.size === 0}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {customizing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                Generating CVs...
              </>
            ) : (
              <>
                ✨ Generate CVs for Selected ({selectedJobIds.size})
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Content ── */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Bulk Results */}
        {bulkResult && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-xl p-6">
            <h3 className="text-lg font-bold text-green-800 mb-4">CV Generation Complete!</h3>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="bg-white rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-gray-900">{bulkResult.total_jobs}</p>
                <p className="text-sm text-gray-500">Total Jobs</p>
              </div>
              <div className="bg-white rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-green-600">{bulkResult.successful_jobs}</p>
                <p className="text-sm text-gray-500">Successful</p>
              </div>
              <div className="bg-white rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-red-600">{bulkResult.failed_jobs}</p>
                <p className="text-sm text-gray-500">Failed</p>
              </div>
            </div>
            
            <div className="max-h-96 overflow-y-auto space-y-2">
              {bulkResult.results.map((result, idx) => (
                <div
                  key={idx}
                  className={`bg-white rounded-lg p-4 border ${
                    result.status === 'success' ? 'border-green-200' : 'border-red-200'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="font-semibold text-gray-900">{result.job_title}</h4>
                      <p className="text-sm text-gray-500">{result.company}</p>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      result.status === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {result.status === 'success' ? '✓ Success' : '✗ Failed'}
                    </span>
                  </div>
                  
                  {result.status === 'success' && result.data && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <div className="mb-2">
                        <p className="text-xs font-medium text-gray-500 mb-1">Tailored Summary</p>
                        <p className="text-sm text-gray-700">{result.data.tailored_summary}</p>
                      </div>
                      
                      {result.data.cover_letter && (
                        <div>
                          <p className="text-xs font-medium text-gray-500 mb-1">Cover Letter</p>
                          <p className="text-sm text-gray-700 whitespace-pre-line">{result.data.cover_letter}</p>
                        </div>
                      )}
                      
                      <div className="mt-3 pt-3 border-t border-gray-100 flex gap-2">
                        <button className="flex-1 bg-blue-600 text-white text-sm py-2 rounded-lg hover:bg-blue-700">
                          Approve & Apply
                        </button>
                        <button className="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50">
                          Edit
                        </button>
                      </div>
                    </div>
                  )}
                  
                  {result.status === 'failed' && result.error && (
                    <p className="mt-2 text-sm text-red-600">Error: {result.error}</p>
                  )}
                </div>
              ))}
            </div>
            
            <button
              onClick={() => setBulkResult(null)}
              className="mt-4 w-full py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50"
            >
              Close Results
            </button>
          </div>
        )}

        {/* Job Count */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-gray-500">
            {loading ? 'Loading...' : `${displayed.length} AI-matched job${displayed.length !== 1 ? 's' : ''} found`}
          </p>
        </div>

        {/* Jobs List */}
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
          </div>
        ) : displayed.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <p className="text-4xl mb-3">🎯</p>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">No AI matches found</h3>
            <p className="text-gray-500 text-sm">
              {!hasCv 
                ? 'Upload your CV to see AI-powered job matches.'
                : 'Try adjusting your search or check back later for new matches.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {displayed.map(job => {
              const score = matchScores[job.id] ?? 0
              const isSelected = selectedJobIds.has(job.id)
              const isSaved = savedIds.has(job.id)
              const isApplied = appliedIds.has(job.id)
              
              return (
                <MatchJobCard
                  key={job.id}
                  job={job}
                  score={score}
                  isSaved={isSaved}
                  isApplied={isApplied}
                  isSelected={isSelected}
                  onSelect={() => toggleJobSelection(job.id)}
                  onSave={() => {/* TODO: implement save */}}
                />
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Match Job Card ───────────────────────────────────────────────────────────

function MatchJobCard({ 
  job, score, isSaved, isApplied, isSelected, onSelect, onSave 
}: {
  job: Job; score: number; isSaved: boolean; isApplied: boolean
  isSelected: boolean; onSelect: () => void; onSave: () => void
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all">
      <div className="p-5">
        {/* Row 1: checkbox + match score + badges */}
        <div className="flex items-center gap-3 mb-3">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onSelect}
            className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
          />
          
          <span className={`text-sm font-bold px-2.5 py-1 rounded-full border ${matchBadge(score)}`}>
            {score}% match
          </span>
          
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SOURCE_COLORS[job.source] || 'bg-gray-100 text-gray-600'}`}>
            {SOURCE_NAMES[job.source] || job.source}
          </span>
          
          {isApplied && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
              Applied
            </span>
          )}
        </div>

        {/* Row 2: title + salary */}
        <div className="flex items-start justify-between gap-3 mb-2">
          <h3 className="text-base font-semibold text-gray-900">{job.title}</h3>
          {(job.salary_min || job.salary_max) && (
            <span className="text-sm font-semibold text-green-600 flex-shrink-0">
              {job.salary_range || `${job.salary_min?.toLocaleString()} – ${job.salary_max?.toLocaleString()}`}
            </span>
          )}
        </div>

        {/* Row 3: company / location / type */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-3 text-sm">
          <span className="font-medium text-gray-700">{job.company}</span>
          {job.location && <span className="text-gray-500">{job.location}</span>}
          {job.job_type && (
            <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded">
              {job.job_type.replace('_', '-')}
            </span>
          )}
        </div>

        {/* Row 4: description snippet */}
        {job.description && (
          <p className="text-sm text-gray-600 mb-3 line-clamp-3">
            {stripHtml(job.description)}
          </p>
        )}

        {/* Row 5: skills */}
        {job.skills_required && job.skills_required.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-4">
            {job.skills_required.slice(0, 5).map((skill, idx) => (
              <span key={idx} className="text-xs bg-gray-50 text-gray-600 px-2 py-0.5 rounded">
                {skill}
              </span>
            ))}
            {job.skills_required.length > 5 && (
              <span className="text-xs text-gray-400">+{job.skills_required.length - 5} more</span>
            )}
          </div>
        )}

        {/* Row 6: actions */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100">
          <button
            onClick={onSave}
            className={`flex items-center gap-1.5 text-sm ${isSaved ? 'text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
          >
            <span className="text-lg">{isSaved ? '★' : '☆'}</span>
            <span>{isSaved ? 'Saved' : 'Save'}</span>
          </button>
          
          <div className="flex gap-2">
            {job.job_url && (
              <a
                href={job.job_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-1.5 border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50"
              >
                View Job
              </a>
            )}
            <button
              onClick={onSelect}
              className={`px-4 py-1.5 text-sm font-medium rounded-lg ${
                isSelected
                  ? 'bg-blue-50 text-blue-700 border border-blue-200'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              {isSelected ? 'Selected' : 'Select for CV'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
