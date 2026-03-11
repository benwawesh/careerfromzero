'use client'

import { useState, useEffect, Fragment } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

// ─── Metadata noise patterns that scrapers sometimes capture ─────────────────
const METADATA_PATTERNS = [
  /share on whatsapp/i, /share on linkedin/i, /share on facebook/i,
  /share link/i, /share via sms/i, /print this job/i,
  /^\d+ (days?|hours?|weeks?|months?) ago$/i,
]

function isMetadataLine(line: string) {
  return METADATA_PATTERNS.some(p => p.test(line.trim()))
}

// ─── Section header detection ─────────────────────────────────────────────────
function isSectionHeader(line: string): boolean {
  const t = line.trim()
  if (!t || t.length > 80) return false
  // Markdown ##, ALL CAPS line, or Title Case ending with colon
  if (/^#{1,3}\s/.test(t)) return true
  if (/^[A-Z][A-Z\s&/\-]{4,}:?$/.test(t)) return true
  if (/^[A-Z][a-zA-Z\s]{2,50}:$/.test(t)) return true
  const keywords = ['about', 'responsibilities', 'requirements', 'qualifications',
    'benefits', 'skills', 'experience', 'education', 'what you', 'who you',
    'the role', 'job summary', 'overview', 'duties', 'what we', 'we offer',
    'key responsibilities', 'key requirements', 'nice to have']
  return keywords.some(k => t.toLowerCase().startsWith(k))
}

function isBulletLine(line: string): boolean {
  return /^[-•*·▪▸►○✓✗→]\s/.test(line.trim()) || /^\d+[.)]\s/.test(line.trim())
}

function stripBullet(line: string): string {
  return line.trim().replace(/^[-•*·▪▸►○✓✗→]\s+/, '').replace(/^\d+[.)]\s+/, '')
}

// Render **bold** and handle escaped \- as bullets
function renderInline(text: string) {
  // Unescape \- → -
  text = text.replace(/\\-/g, '-').replace(/\\\*/g, '*')
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : <Fragment key={i}>{part}</Fragment>
  )
}

// ─── Render plain text with section detection ─────────────────────────────────
function PlainTextDescription({ text }: { text: string }) {
  const lines = text.split(/\n/).map(l => l.trim()).filter(l => l && !isMetadataLine(l))

  type Block =
    | { type: 'heading'; text: string }
    | { type: 'bullets'; items: string[] }
    | { type: 'paragraph'; text: string }

  const blocks: Block[] = []
  let currentBullets: string[] | null = null

  const flushBullets = () => {
    if (currentBullets && currentBullets.length > 0) {
      blocks.push({ type: 'bullets', items: currentBullets })
      currentBullets = null
    }
  }

  for (const line of lines) {
    if (isSectionHeader(line)) {
      flushBullets()
      blocks.push({ type: 'heading', text: line.replace(/^#{1,3}\s+/, '').replace(/:$/, '') })
    } else if (isBulletLine(line)) {
      if (!currentBullets) currentBullets = []
      currentBullets.push(stripBullet(line))
    } else {
      flushBullets()
      const last = blocks[blocks.length - 1]
      if (last && last.type === 'paragraph') {
        last.text += ' ' + line
      } else {
        blocks.push({ type: 'paragraph', text: line })
      }
    }
  }
  flushBullets()

  return (
    <div className="space-y-3 text-gray-700 leading-relaxed">
      {blocks.map((block, i) => {
        if (block.type === 'heading') {
          return (
            <h3 key={i} className="text-base font-semibold text-gray-900 mt-5 first:mt-0 pb-1 border-b border-gray-100">
              {block.text}
            </h3>
          )
        }
        if (block.type === 'bullets') {
          return (
            <ul key={i} className="list-disc list-outside ml-5 space-y-1">
              {block.items.map((item, j) => <li key={j}>{renderInline(item)}</li>)}
            </ul>
          )
        }
        return <p key={i}>{renderInline(block.text)}</p>
      })}
    </div>
  )
}

// ─── Main description component with live-fetch fallback ─────────────────────
function JobDescription({
  jobId, description, jobUrl, source,
}: {
  jobId: string; description: string; jobUrl?: string; source: string;
}) {
  const [liveHtml, setLiveHtml] = useState<string | null>(null)
  const [liveText, setLiveText] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const storedText = (description || '').trim()
  const hasStoredDesc = storedText && storedText !== 'nan' && storedText.length >= 50

  // Sources where we always fetch live description (stored desc is usually scraped metadata noise)
  const LIVE_SOURCES = ['brightermonday', 'myjobmag', 'corporatestaffing',
    'jobwebkenya', 'kenyajob', 'nationkenya', 'ngojobs', 'jobberman', 'career24']
  const shouldAutoLoad = LIVE_SOURCES.includes(source)

  async function loadLiveDescription() {
    setLoading(true)
    setError(null)
    try {
      const r = await apiFetch(`/api/jobs/jobs/${jobId}/fetch_description/`)
      if (r.ok) {
        const data = await r.json()
        setLiveHtml(data.description_html || null)
        setLiveText(data.description_text || null)
      } else {
        const data = await r.json().catch(() => ({}))
        setError(data.error || 'Could not load description')
      }
    } catch {
      setError('Network error — try again')
    } finally {
      setLoading(false)
    }
  }

  // Auto-load for local job boards that never have stored descriptions
  useEffect(() => {
    if (shouldAutoLoad) loadLiveDescription()
  }, [jobId])

  // ── Render live-fetched content ──────────────────────────────────────────
  if (liveHtml || liveText) {
    const cleanHtml = liveHtml
      ? liveHtml
          .replace(/<script[\s\S]*?<\/script>/gi, '')
          .replace(/<style[\s\S]*?<\/style>/gi, '')
      : null
    return (
      <div>
        {cleanHtml ? (
          <div
            className="prose prose-gray max-w-none prose-headings:text-gray-900 prose-headings:font-semibold prose-headings:mt-5 prose-li:text-gray-700 prose-p:text-gray-700 prose-strong:text-gray-900 prose-ul:list-disc prose-ul:ml-4"
            dangerouslySetInnerHTML={{ __html: cleanHtml }}
          />
        ) : (
          <PlainTextDescription text={liveText!} />
        )}
      </div>
    )
  }

  // ── Loading state ────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center gap-3 py-8 text-gray-500">
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600" />
        <span>Loading description from {source}…</span>
      </div>
    )
  }

  // ── Stored description present ───────────────────────────────────────────
  if (hasStoredDesc) {
    if (/<[a-z][\s\S]*?>/i.test(storedText)) {
      const cleaned = storedText
        .replace(/<script[\s\S]*?<\/script>/gi, '')
        .replace(/<style[\s\S]*?<\/style>/gi, '')
      return (
        <div
          className="prose prose-gray max-w-none prose-headings:text-gray-900 prose-headings:font-semibold prose-li:text-gray-700 prose-p:text-gray-700 prose-strong:text-gray-900"
          dangerouslySetInnerHTML={{ __html: cleaned }}
        />
      )
    }
    return <PlainTextDescription text={storedText} />
  }

  // ── Live fetch failed — fall back to stored description if present ──────
  if (error && hasStoredDesc) {
    return <PlainTextDescription text={storedText} />
  }

  // ── No description available ─────────────────────────────────────────────
  return (
    <div className="space-y-4">
      {error && (
        <p className="text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">{error}</p>
      )}
      <div className="flex flex-col items-center gap-3 py-6 text-gray-500">
        {jobUrl && (
          <button
            onClick={loadLiveDescription}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading
              ? <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> Loading…</>
              : <>Load Full Description</>}
          </button>
        )}
        {jobUrl && (
          <a href={jobUrl} target="_blank" rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:underline flex items-center gap-1">
            Or view on source site
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        )}
      </div>
    </div>
  )
}

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
  is_featured?: boolean
  requirements?: string[]
  responsibilities?: string[]
  benefits?: string[]
}

export default function JobDetailPage() {
  return (
    <ProtectedRoute>
      <JobDetail />
    </ProtectedRoute>
  )
}

function JobDetail() {
  const params = useParams()
  const router = useRouter()
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [isSaved, setIsSaved] = useState(false)
  const [applying, setApplying] = useState(false)
  const [showApplyModal, setShowApplyModal] = useState(false)
  const [coverLetter, setCoverLetter] = useState('')

  useEffect(() => {
    if (params.id) {
      fetchJob()
    }
  }, [params.id])

  async function fetchJob() {
    setLoading(true)
    try {
      const r = await apiFetch(`/api/jobs/jobs/${params.id}/`)
      if (r.ok) {
        const data = await r.json()
        setJob(data)
        // Check if saved
        const savedR = await apiFetch(`/api/jobs/jobs/${params.id}/check_saved/`)
        if (savedR.ok) {
          const savedData = await savedR.json()
          setIsSaved(savedData.saved)
        }
      }
    } finally {
      setLoading(false)
    }
  }

  async function toggleSave() {
    setSaving(true)
    try {
      if (isSaved) {
        await apiFetch(`/api/jobs/jobs/${params.id}/unsave/`, { method: 'DELETE' })
      } else {
        await apiFetch(`/api/jobs/jobs/${params.id}/save/`, { method: 'POST' })
      }
      setIsSaved(!isSaved)
    } catch (e) {
      console.error('Failed to toggle save:', e)
    } finally {
      setSaving(false)
    }
  }

  async function handleApply() {
    setApplying(true)
    try {
      const r = await apiFetch(`/api/jobs/jobs/${params.id}/apply/`, {
        method: 'POST',
        body: JSON.stringify({ cover_letter: coverLetter }),
      })
      if (r.ok) {
        alert('Application submitted successfully!')
        setShowApplyModal(false)
        setCoverLetter('')
      } else {
        const data = await r.json()
        alert(data.detail || 'Failed to apply')
      }
    } catch (e) {
      console.error('Failed to apply:', e)
      alert('Failed to apply')
    } finally {
      setApplying(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-700" />
      </div>
    )
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-4xl mb-3">😕</p>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">Job not found</h3>
          <Link
            href="/jobs"
            className="text-blue-600 hover:underline"
          >
            Back to jobs
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link
              href="/jobs"
              className="text-gray-600 hover:text-gray-900 flex items-center gap-1"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Jobs
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content (2/3) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Job Header */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h1 className="text-2xl font-bold text-gray-900 mb-2">{job.title}</h1>
                  <p className="text-lg text-gray-600 mb-3">{job.company}</p>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center px-3 py-1 rounded text-sm font-medium bg-blue-50 text-blue-700">
                      {job.location}
                    </span>
                    {job.job_type && (
                      <span className="inline-flex items-center px-3 py-1 rounded text-sm font-medium bg-green-50 text-green-700">
                        {job.job_type.replace('_', ' ')}
                      </span>
                    )}
                    {job.experience_level && (
                      <span className="inline-flex items-center px-3 py-1 rounded text-sm font-medium bg-purple-50 text-purple-700">
                        {job.experience_level.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={toggleSave}
                  disabled={saving}
                  className={`ml-4 p-3 rounded-lg transition-colors ${
                    isSaved
                      ? 'text-yellow-500 hover:bg-yellow-50'
                      : 'text-gray-400 hover:bg-gray-100'
                  }`}
                >
                  {saving ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-current" />
                  ) : (
                    <svg className="w-6 h-6" fill={isSaved ? 'currentColor' : 'none'} viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  )}
                </button>
              </div>

              {/* Salary */}
              {(job.salary_range || job.salary_min || job.salary_max) && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Salary</h3>
                  <p className="text-lg font-semibold text-gray-900">
                    {job.salary_range || 
                      (job.salary_min && job.salary_max 
                        ? `$${job.salary_min.toLocaleString()} - $${job.salary_max.toLocaleString()}`
                        : job.salary_min 
                        ? `$${job.salary_min.toLocaleString()}+`
                        : job.salary_max 
                        ? `Up to $${job.salary_max.toLocaleString()}`
                        : 'Not specified')}
                  </p>
                </div>
              )}

              {/* Stats */}
              <div className="flex items-center gap-6 text-sm text-gray-500 mb-4">
                <div className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  {job.view_count || 0} views
                </div>
                <div className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  {job.application_count || 0} applications
                </div>
                {job.posted_date && (
                  <div className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    Posted {new Date(job.posted_date).toLocaleDateString()}
                  </div>
                )}
              </div>

              {/* Source Badge */}
              <div className="mb-4">
                <span className="text-sm text-gray-500">Source: </span>
                <span className="text-sm font-medium text-gray-900 capitalize">{job.source}</span>
              </div>
            </div>

            {/* Job Description */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Job Description</h2>
              <JobDescription
                jobId={job.id}
                description={job.description}
                jobUrl={job.job_url}
                source={job.source}
              />
            </div>

            {/* Requirements */}
            {job.requirements && job.requirements.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Requirements</h2>
                <ul className="list-disc list-inside space-y-2 text-gray-700">
                  {job.requirements.map((req, idx) => (
                    <li key={idx}>{req}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Skills Required */}
            {job.skills_required && job.skills_required.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Skills Required</h2>
                <div className="flex flex-wrap gap-2">
                  {job.skills_required.map((skill, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-700"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Responsibilities */}
            {job.responsibilities && job.responsibilities.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Responsibilities</h2>
                <ul className="list-disc list-inside space-y-2 text-gray-700">
                  {job.responsibilities.map((resp, idx) => (
                    <li key={idx}>{resp}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Benefits */}
            {job.benefits && job.benefits.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Benefits</h2>
                <ul className="list-disc list-inside space-y-2 text-gray-700">
                  {job.benefits.map((benefit, idx) => (
                    <li key={idx}>{benefit}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Sidebar (1/3) */}
          <div className="space-y-6">
            {/* Apply Button */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <button
                onClick={() => setShowApplyModal(true)}
                className="w-full px-6 py-3 bg-red-700 text-white text-lg font-semibold rounded-lg hover:bg-red-800 transition-colors mb-3"
              >
                Apply Now
              </button>
              {job.job_url && (
                <a
                  href={job.job_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full px-6 py-3 bg-gray-100 text-gray-700 text-lg font-semibold rounded-lg hover:bg-gray-200 transition-colors text-center"
                >
                  View on Source Site
                </a>
              )}
            </div>

            {/* Company Info */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">About {job.company}</h3>
              <p className="text-gray-600 text-sm">
                This job is sourced from {job.source}. Click "View on Source Site" to learn more about the company.
              </p>
            </div>

            {/* Share Job */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Share this job</h3>
              <button
                onClick={() => {
                  if (navigator.share) {
                    navigator.share({
                      title: job.title,
                      text: `Check out this job: ${job.title} at ${job.company}`,
                      url: window.location.href,
                    })
                  }
                }}
                className="w-full px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                Share Job
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Apply Modal */}
      {showApplyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-gray-900">Apply for {job.title}</h2>
              <button
                onClick={() => setShowApplyModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Cover Letter (Optional)
                </label>
                <textarea
                  value={coverLetter}
                  onChange={(e) => setCoverLetter(e.target.value)}
                  placeholder="Write a cover letter explaining why you're a good fit for this position..."
                  rows={6}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleApply}
                  disabled={applying}
                  className="flex-1 px-6 py-3 bg-red-700 text-white font-semibold rounded-lg hover:bg-red-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {applying ? 'Submitting...' : 'Submit Application'}
                </button>
                <button
                  onClick={() => setShowApplyModal(false)}
                  className="px-6 py-3 bg-gray-100 text-gray-700 font-semibold rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
              </div>

              <p className="text-sm text-gray-500 text-center">
                Your current CV will be attached automatically
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}