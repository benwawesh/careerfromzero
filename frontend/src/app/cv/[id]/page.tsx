'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

type Tab = 'overview' | 'analysis' | 'tailor'
type UUID = string

interface CVData {
  email?: string
  phone?: string
  location?: string
  linkedin_url?: string
  github_url?: string
  summary?: string
  raw_text?: string
  skills: string[]
  experience: { role: string; company: string; duration: string }[]
  education: { degree: string; institution: string; year: string }[]
  projects: { name: string; description: string }[]
  certifications: string[]
  languages: string[]
  parsing_status: string
}

interface DetailedCheck {
  name: string
  status: 'pass' | 'fail'
  issues: number
  details: string
}

interface DetailedCategory {
  score: number
  checks: DetailedCheck[]
}

interface DetailedChecks {
  content?: DetailedCategory
  formatting?: DetailedCategory
  keywords?: DetailedCategory
}

interface CVAnalysis {
  ats_score: number
  overall_score: number
  content_quality_score: number
  formatting_score: number
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
  formatting_issues: string[]
  missing_keywords: string[]
  missing_sections: string[]
  analysis_status: string
  detailed_checks?: DetailedChecks
}

interface CVVersion {
  id: UUID
  title: string
  version_type: string
  version_number: number
  ats_score?: number
  overall_score?: number
  keywords_added?: string[]
  changes_made?: string[]
  is_current: boolean
  created_at: string
  description?: string
  optimization_target?: string
  optimized_text?: string
}

interface CVVersionDetail {
  version: CVVersion
  cv_data: {
    email?: string
    phone?: string
    location?: string
    linkedin_url?: string
    github_url?: string
    website_url?: string
    summary?: string
    skills: string[]
    experience: { role: string; company: string; duration: string; description?: string }[]
    education: { degree: string; institution: string; year: string }[]
    projects: { name: string; description: string; technologies?: string }[]
    certifications: string[]
    languages: string[]
    interests?: string[]
  }
}

interface CV {
  id: UUID
  title: string
  original_filename: string
  file_type: string
  file_size: number
  is_parsed: boolean
  is_analyzed: boolean
  uploaded_at: string
  data?: CVData
  analysis?: CVAnalysis
  versions: CVVersion[]
}

// Agent steps shown during analysis
const ANALYSIS_STEPS = [
  { agent: 'CV Parser Agent', action: 'Reading and structuring your CV…', icon: '📄' },
  { agent: 'ATS Analyst Agent', action: 'Scoring ATS compatibility and finding gaps…', icon: '🔍' },
  { agent: 'ATS Analyst Agent', action: 'Generating prioritised recommendations…', icon: '📊' },
  { agent: 'System', action: 'Finalising analysis report…', icon: '✅' },
]

const TAILOR_STEPS = [
  { agent: 'Job Analyst Agent', action: 'Extracting job requirements and keywords…', icon: '💼' },
  { agent: 'Gap Analyst Agent', action: 'Comparing your CV against job requirements…', icon: '🔄' },
  { agent: 'CV Writer Agent', action: 'Rewriting CV to match the role…', icon: '✍️' },
  { agent: 'CV Writer Agent', action: 'Optimising keywords and impact statements…', icon: '🚀' },
  { agent: 'System', action: 'Saving tailored CV version…', icon: '✅' },
]

// ── Full CV Document Preview ────────────────────────────────────────────────

function CVFullPreview({ rawText }: { rawText: string }) {
  const [expanded, setExpanded] = useState(false)

  // Detect section headers: all-caps lines or lines ending with a colon
  const SECTION_RE = /^(PROFESSIONAL SUMMARY|SUMMARY|OBJECTIVE|WORK EXPERIENCE|EXPERIENCE|EDUCATION|SKILLS|TECHNICAL SKILLS|PROJECTS|CERTIFICATIONS|LANGUAGES|ACHIEVEMENTS|AWARDS|PUBLICATIONS|REFERENCES|VOLUNTEER|INTERESTS|PROFILE)[\s:]*$/i

  const lines = rawText.split('\n')
  const previewLines = expanded ? lines : lines.slice(0, 40)

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      <div className="p-6 border-b border-gray-100 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Full CV Document</h2>
        <button
          onClick={() => setExpanded(v => !v)}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          {expanded ? 'Show less ▲' : 'Show full CV ▼'}
        </button>
      </div>

      {/* A4-like white paper look */}
      <div className="bg-gray-100 p-4">
        <div className="bg-white shadow-md rounded max-w-3xl mx-auto p-8 font-serif text-[13px] leading-relaxed text-gray-800">
          {previewLines.map((line, i) => {
            const trimmed = line.trim()
            if (!trimmed) return <div key={i} className="h-3" />

            if (SECTION_RE.test(trimmed)) {
              return (
                <div key={i} className="mt-5 mb-1">
                  <h3 className="font-sans font-bold text-[11px] uppercase tracking-widest text-blue-800 border-b border-blue-200 pb-1">
                    {trimmed.replace(/:$/, '')}
                  </h3>
                </div>
              )
            }

            if (trimmed.startsWith('-') || trimmed.startsWith('•') || trimmed.startsWith('–')) {
              return (
                <p key={i} className="ml-4 before:content-['•'] before:mr-2 before:text-gray-400">
                  {trimmed.replace(/^[-•–]\s*/, '')}
                </p>
              )
            }

            return <p key={i}>{trimmed}</p>
          })}

          {!expanded && lines.length > 40 && (
            <div className="text-center mt-4">
              <button
                onClick={() => setExpanded(true)}
                className="text-sm text-blue-600 hover:underline font-sans"
              >
                + {lines.length - 40} more lines — click to expand
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function CVDetailPage() {
  return (
    <ProtectedRoute>
      <CVDetail />
    </ProtectedRoute>
  )
}

function CVDetail() {
  const { id } = useParams()
  const router = useRouter()
  const [cv, setCv] = useState<CV | null>(null)
  const [tab, setTab] = useState<Tab>('overview')
  const [loading, setLoading] = useState(true)

  // Analysis state
  const [analysisRunning, setAnalysisRunning] = useState(false)
  const [analysisStep, setAnalysisStep] = useState(0)
  const pollRef = useRef<NodeJS.Timeout | null>(null)
  const stepRef = useRef<NodeJS.Timeout | null>(null)

  // Tailor state
  const [tailorRunning, setTailorRunning] = useState(false)
  const [tailorStep, setTailorStep] = useState(0)
  const [jobDescription, setJobDescription] = useState('')
  const [jobTitle, setJobTitle] = useState('')
  const [jobCompany, setJobCompany] = useState('')
  const [tailorDone, setTailorDone] = useState(false)
  
  // Version viewing state
  const [viewingVersion, setViewingVersion] = useState<CVVersionDetail | null>(null)
  const [loadingVersion, setLoadingVersion] = useState(false)
  const [downloadingPDF, setDownloadingPDF] = useState<UUID | null>(null)

  const [error, setError] = useState('')

  useEffect(() => {
    fetchCV()
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (stepRef.current) clearInterval(stepRef.current)
    }
  }, [id])

  const fetchCV = async () => {
    setLoading(true)
    try {
      const res = await apiFetch(`/api/cv/${id}/`)
      if (res.ok) {
        setCv(await res.json())
      } else {
        router.push('/cv')
      }
    } catch {
      setError('Failed to load CV')
    } finally {
      setLoading(false)
    }
  }

  // ── Analysis ─────────────────────────────────────────────────────

  const startAnalysis = async () => {
    setError('')
    setAnalysisRunning(true)
    setAnalysisStep(0)
    setTab('analysis')

    try {
      const res = await apiFetch(`/api/cv/${id}/analyze/`, { method: 'POST' })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.error || 'Failed to start analysis')
        setAnalysisRunning(false)
        return
      }

      // Advance step display every ~50 seconds (4 steps × 50s ≈ 3 min visible progress)
      let step = 0
      stepRef.current = setInterval(() => {
        step = Math.min(step + 1, ANALYSIS_STEPS.length - 1)
        setAnalysisStep(step)
      }, 50000)

      // Poll until is_analyzed = true (max 15 minutes on CPU)
      let pollCount = 0
      pollRef.current = setInterval(async () => {
        pollCount++
        if (pollCount > 225) { // 225 × 4s = 15 min
          clearInterval(pollRef.current!)
          clearInterval(stepRef.current!)
          setAnalysisRunning(false)
          setError('Analysis timed out. Check that Ollama is running (ollama serve).')
          return
        }
        const poll = await apiFetch(`/api/cv/${id}/`)
        if (poll.ok) {
          const data: CV = await poll.json()
          const status = data.analysis?.analysis_status
          if (status === 'completed') {
            clearInterval(pollRef.current!)
            clearInterval(stepRef.current!)
            setAnalysisRunning(false)
            setAnalysisStep(ANALYSIS_STEPS.length - 1)
            setCv(data)
          } else if (status === 'failed') {
            clearInterval(pollRef.current!)
            clearInterval(stepRef.current!)
            setAnalysisRunning(false)
            setError('Analysis failed. Check that Ollama is running (ollama serve).')
          }
        }
      }, 4000)
    } catch {
      setError('Network error. Is the backend running?')
      setAnalysisRunning(false)
    }
  }

  // ── Tailoring ─────────────────────────────────────────────────────

  const startTailor = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setTailorRunning(true)
    setTailorStep(0)
    setTailorDone(false)

    try {
      // 1. Save the job description
      const jobRes = await apiFetch(`/api/cv/${id}/jobs/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: jobTitle || 'Target Job',
          company: jobCompany || 'Target Company',
          description: jobDescription,
        }),
      })

      if (!jobRes.ok) {
        setError('Failed to save job description')
        setTailorRunning(false)
        return
      }

      const job = await jobRes.json()

      // 2. Start tailoring crew
      const optRes = await apiFetch(`/api/cv/${id}/optimize/${job.id}/`, { method: 'POST' })

      if (!optRes.ok) {
        const data = await optRes.json().catch(() => ({}))
        setError(data.error || 'Failed to start tailoring')
        setTailorRunning(false)
        return
      }

      const prevVersionCount = cv?.versions?.length ?? 0

      // Advance step display every 20 seconds (5 steps × 20s ≈ visible progress during ~60s AI call)
      let step = 0
      stepRef.current = setInterval(() => {
        step = Math.min(step + 1, TAILOR_STEPS.length - 1)
        setTailorStep(step)
      }, 20000)

      // Poll until a new version appears (max 5 minutes)
      let tailorPollCount = 0
      pollRef.current = setInterval(async () => {
        tailorPollCount++
        if (tailorPollCount > 75) { // 75 × 4s = 5 min
          clearInterval(pollRef.current!)
          clearInterval(stepRef.current!)
          setTailorRunning(false)
          setError('Tailoring timed out. Please try again.')
          return
        }
        const poll = await apiFetch(`/api/cv/${id}/`)
        if (poll.ok) {
          const data: CV = await poll.json()
          if (data.versions.length > prevVersionCount) {
            clearInterval(pollRef.current!)
            clearInterval(stepRef.current!)
            setTailorRunning(false)
            setTailorStep(TAILOR_STEPS.length - 1)
            setTailorDone(true)
            setCv(data)
          }
        }
      }, 4000)
    } catch {
      setError('Network error. Is the backend running?')
      setTailorRunning(false)
    }
  }

  // ── Version Viewing & Download ─────────────────────────────────────

  const viewVersion = async (versionId: UUID) => {
    setLoadingVersion(true)
    setError('')
    try {
      const res = await apiFetch(`/api/cv/${id}/versions/${versionId}/`)
      if (res.ok) {
        const data = await res.json()
        console.log('Version data:', data) // Debug log
        // Ensure that data has a expected structure
        if (data && data.version && data.cv_data) {
          setViewingVersion(data)
        } else {
          setError('Invalid version data received from server')
          setViewingVersion(null) // Don't set invalid data
        }
      } else {
        const data = await res.json().catch(() => ({}))
        setError(data.error || 'Failed to load version')
      }
    } catch (err) {
      console.error('Error viewing version:', err)
      setError('Network error. Is the backend running?')
    } finally {
      setLoadingVersion(false)
    }
  }

  const downloadPDF = async (versionId: UUID) => {
    setDownloadingPDF(versionId)
    try {
      // Use apiFetch to get automatic token refresh
      const response = await apiFetch(`/api/cv/${id}/versions/${versionId}/download/`)

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setError(data.error || `Failed to download PDF (Status: ${response.status})`)
        return
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const version = cv?.versions.find(v => v.id === versionId)
      a.download = `${cv?.title.replace(' ', '_')}_v${version?.version_number || versionId}.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

    } catch (err) {
      console.error('PDF download error:', err)
      setError('Network error. Failed to download PDF')
    } finally {
      setDownloadingPDF(null)
    }
  }

  // ── Rendering helpers ─────────────────────────────────────────────

  const ScoreRing = ({
    score, label, color,
  }: { score: number; label: string; color: string }) => (
    <div className="flex flex-col items-center">
      <div className={`w-20 h-20 rounded-full border-4 ${color} flex items-center justify-center`}>
        <span className="text-xl font-bold text-gray-900">{score}</span>
      </div>
      <p className="text-sm text-gray-600 mt-2 text-center">{label}</p>
    </div>
  )

  const AgentProgressPanel = ({
    steps, currentStep, running, doneLabel,
  }: {
    steps: typeof ANALYSIS_STEPS
    currentStep: number
    running: boolean
    doneLabel: string
  }) => (
    <div className="bg-white rounded-xl shadow-md p-6 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <div className={`w-3 h-3 rounded-full ${running ? 'bg-blue-500 animate-pulse' : 'bg-green-500'}`} />
        <span className="text-sm font-semibold text-gray-700">
          {running ? 'AI Agents Working…' : doneLabel}
        </span>
      </div>
      <div className="space-y-3">
        {steps.map((step, i) => {
          const done = i < currentStep || (!running && i <= currentStep)
          const active = i === currentStep && running
          return (
            <div key={i} className={`flex items-start gap-3 p-3 rounded-lg transition-all ${
              active ? 'bg-blue-50 border border-blue-200' :
              done ? 'bg-green-50' : 'bg-gray-50 opacity-40'
            }`}>
              <span className="text-lg flex-shrink-0">{step.icon}</span>
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  {step.agent}
                </p>
                <p className={`text-sm ${active ? 'text-blue-700 font-medium' : done ? 'text-green-700' : 'text-gray-500'}`}>
                  {done && !active ? '✓ ' : active ? '' : ''}{step.action}
                </p>
              </div>
              {active && (
                <div className="ml-auto flex-shrink-0">
                  <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                </div>
              )}
              {done && !active && (
                <span className="ml-auto text-green-500 flex-shrink-0">✓</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
    </div>
  )
  if (!cv) return null

  const analysis = cv.analysis

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/cv" className="text-gray-400 hover:text-gray-600 text-sm">← CVs</Link>
              <div>
                <h1 className="text-xl font-bold text-gray-900">{cv.title}</h1>
                <p className="text-sm text-gray-500">{cv.original_filename} · {cv.file_type}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <a
                href={`/api/cv/${id}/download-original/`}
                onClick={async (e) => {
                  e.preventDefault()
                  const res = await apiFetch(`/api/cv/${id}/download-original/`)
                  if (!res.ok) { setError('Download failed'); return }
                  const blob = await res.blob()
                  const url = window.URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = cv.original_filename || 'cv'
                  document.body.appendChild(a)
                  a.click()
                  window.URL.revokeObjectURL(url)
                  document.body.removeChild(a)
                }}
                className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 flex items-center gap-1"
              >
                📥 Download Original
              </a>
              {cv.is_parsed && !analysisRunning && (
                <button
                  onClick={startAnalysis}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    cv.is_analyzed
                      ? 'border border-purple-300 text-purple-600 hover:bg-purple-50'
                      : 'bg-purple-600 text-white hover:bg-purple-700'
                  }`}
                >
                  {cv.is_analyzed ? 'Re-analyse' : 'Run ATS Analysis'}
                </button>
              )}
              {analysisRunning && (
                <span className="text-sm text-blue-600 font-medium animate-pulse">
                  Agents running…
                </span>
              )}
            </div>
          </div>

          {/* Tabs */}
          <div className="flex space-x-1 mt-4 border-b border-gray-200">
            {(['overview', 'analysis', 'tailor'] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  tab === t
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {t === 'tailor' ? 'Tailor to Job' : t.charAt(0).toUpperCase() + t.slice(1)}
                {t === 'analysis' && analysis?.analysis_status === 'processing' && (
                  <span className="ml-1 w-2 h-2 inline-block rounded-full bg-blue-500 animate-pulse" />
                )}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg mb-6 flex justify-between">
            <span>{error}</span>
            <button onClick={() => setError('')} className="text-red-400 hover:text-red-600">✕</button>
          </div>
        )}

        {/* ── OVERVIEW TAB ─────────────────────────────────────── */}
        {tab === 'overview' && (
          <div className="space-y-6">
            {!cv.is_parsed ? (
              <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-lg">
                This CV is still being parsed. Refresh in a moment.
              </div>
            ) : cv.data ? (
              <>
                <div className="bg-white rounded-xl shadow-md p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Contact Information</h2>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    {cv.data.email && <div><span className="text-gray-500">Email: </span><span className="font-medium">{cv.data.email}</span></div>}
                    {cv.data.phone && <div><span className="text-gray-500">Phone: </span><span className="font-medium">{cv.data.phone}</span></div>}
                    {cv.data.location && <div><span className="text-gray-500">Location: </span><span className="font-medium">{cv.data.location}</span></div>}
                    {cv.data.linkedin_url && <div><span className="text-gray-500">LinkedIn: </span><a href={cv.data.linkedin_url} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">Profile</a></div>}
                    {cv.data.github_url && <div><span className="text-gray-500">GitHub: </span><a href={cv.data.github_url} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">Profile</a></div>}
                  </div>
                </div>

                {cv.data.summary && (
                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-3">Summary</h2>
                    <p className="text-gray-700">{cv.data.summary}</p>
                  </div>
                )}

                {cv.data.skills?.length > 0 && (
                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Skills ({cv.data.skills.length})</h2>
                    <div className="flex flex-wrap gap-2">
                      {cv.data.skills.map((s, i) => (
                        <span key={i} className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm font-medium">{s}</span>
                      ))}
                    </div>
                  </div>
                )}

                {cv.data.experience?.length > 0 && (
                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Experience</h2>
                    <div className="space-y-4">
                      {cv.data.experience.map((exp, i) => (
                        <div key={i} className="border-l-2 border-blue-200 pl-4">
                          <p className="font-semibold text-gray-900">{exp.role}</p>
                          <p className="text-blue-600">{exp.company}</p>
                          <p className="text-sm text-gray-500">{exp.duration}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {cv.data.education?.length > 0 && (
                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Education</h2>
                    <div className="space-y-4">
                      {cv.data.education.map((edu, i) => (
                        <div key={i} className="border-l-2 border-purple-200 pl-4">
                          <p className="font-semibold text-gray-900">{edu.degree}</p>
                          <p className="text-purple-600">{edu.institution}</p>
                          <p className="text-sm text-gray-500">{edu.year}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid md:grid-cols-2 gap-6">
                  {cv.data.certifications?.length > 0 && (
                    <div className="bg-white rounded-xl shadow-md p-6">
                      <h2 className="text-lg font-semibold text-gray-900 mb-3">Certifications</h2>
                      <ul className="space-y-2">
                        {cv.data.certifications.map((c, i) => (
                          <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                            <span className="text-green-500 mt-0.5">✓</span>{c}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {cv.data.languages?.length > 0 && (
                    <div className="bg-white rounded-xl shadow-md p-6">
                      <h2 className="text-lg font-semibold text-gray-900 mb-3">Languages</h2>
                      <div className="flex flex-wrap gap-2">
                        {cv.data.languages.map((l, i) => (
                          <span key={i} className="bg-green-50 text-green-700 px-3 py-1 rounded-full text-sm">{l}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Tailored versions quick-access */}
                {cv.versions?.length > 0 && (
                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Tailored Versions ({cv.versions.length})</h2>
                    <div className="space-y-3">
                      {cv.versions.map((v) => (
                        <div key={v.id} className="flex items-center justify-between p-3 border border-gray-100 rounded-lg">
                          <div>
                            <p className="font-medium text-sm text-gray-900">{v.title}</p>
                            <p className="text-xs text-gray-500">Version {v.version_number} · {v.version_type === 'job_tailored' ? 'Job Tailored' : 'ATS Optimised'}</p>
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={() => viewVersion(v.id)}
                              className="text-sm px-3 py-1.5 border border-blue-300 text-blue-600 rounded-lg hover:bg-blue-50"
                            >
                              View
                            </button>
                            <button
                              onClick={() => downloadPDF(v.id)}
                              disabled={downloadingPDF === v.id}
                              className="text-sm px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
                            >
                              {downloadingPDF === v.id ? '⏳' : '📥'} PDF
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Full CV text preview */}
                {cv.data.raw_text && (
                  <CVFullPreview rawText={cv.data.raw_text} />
                )}
              </>
            ) : null}
          </div>
        )}

        {/* ── ANALYSIS TAB ─────────────────────────────────────── */}
        {tab === 'analysis' && (
          <div className="space-y-6">
            {analysisRunning && (
              <AgentProgressPanel
                steps={ANALYSIS_STEPS}
                currentStep={analysisStep}
                running={analysisRunning}
                doneLabel="Analysis complete"
              />
            )}

            {!analysisRunning && (!cv.is_analyzed || !analysis) && (
              <div className="bg-white rounded-xl shadow-md p-12 text-center">
                <div className="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">🤖</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">No analysis yet</h3>
                <p className="text-gray-500 mb-2">
                  Two AI agents will analyse your CV:
                </p>
                <div className="flex justify-center gap-4 mb-6 text-sm text-gray-600">
                  <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full">📄 CV Parser Agent</span>
                  <span className="text-gray-400">→</span>
                  <span className="bg-purple-50 text-purple-700 px-3 py-1 rounded-full">🔍 ATS Analyst Agent</span>
                </div>
                <button
                  onClick={startAnalysis}
                  disabled={!cv.is_parsed}
                  className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 disabled:opacity-50"
                >
                  {!cv.is_parsed ? 'CV not parsed yet' : 'Start AI Analysis'}
                </button>
              </div>
            )}

            {!analysisRunning && cv.is_analyzed && analysis && (
              <>
                {/* Score rings */}
                <div className="bg-white rounded-xl shadow-md p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-semibold text-gray-900">Score Breakdown</h2>
                    <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 px-3 py-1 rounded-full">
                      <span>🤖</span>
                      <span>Powered by CV Parser + ATS Analyst agents</span>
                    </div>
                  </div>
                  <div className="flex justify-around flex-wrap gap-6">
                    <ScoreRing score={analysis.ats_score} label="ATS Score" color="border-blue-500" />
                    <ScoreRing score={analysis.overall_score} label="Overall" color="border-purple-500" />
                    <ScoreRing score={analysis.content_quality_score} label="Content" color="border-green-500" />
                    <ScoreRing score={analysis.formatting_score} label="Formatting" color="border-orange-500" />
                  </div>
                </div>

                {/* Detailed itemized checks */}
                {analysis.detailed_checks && Object.keys(analysis.detailed_checks).length > 0 && (
                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-5">Detailed Checks</h2>
                    <div className="space-y-6">
                      {(['content', 'formatting', 'keywords'] as const).map((cat) => {
                        const category = analysis.detailed_checks?.[cat]
                        if (!category) return null
                        const catLabel = cat === 'content' ? 'CONTENT' : cat === 'formatting' ? 'FORMATTING' : 'KEYWORDS'
                        const catColor = cat === 'content' ? 'text-green-700 bg-green-50 border-green-200' : cat === 'formatting' ? 'text-orange-700 bg-orange-50 border-orange-200' : 'text-blue-700 bg-blue-50 border-blue-200'
                        const barColor = cat === 'content' ? 'bg-green-500' : cat === 'formatting' ? 'bg-orange-500' : 'bg-blue-500'
                        return (
                          <div key={cat}>
                            <div className={`flex items-center justify-between px-4 py-2 rounded-lg border mb-2 ${catColor}`}>
                              <span className="font-semibold text-sm tracking-wide">{catLabel}</span>
                              <div className="flex items-center gap-2">
                                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                                  <div className={`h-full rounded-full ${barColor}`} style={{ width: `${category.score}%` }} />
                                </div>
                                <span className="text-sm font-bold">{category.score}%</span>
                              </div>
                            </div>
                            <div className="divide-y divide-gray-100 border border-gray-100 rounded-lg overflow-hidden">
                              {category.checks.map((check, i) => (
                                <div key={i} className="flex items-start gap-3 px-4 py-3 bg-white hover:bg-gray-50 transition-colors">
                                  <span className={`mt-0.5 flex-shrink-0 text-base ${check.status === 'pass' ? 'text-green-500' : 'text-red-500'}`}>
                                    {check.status === 'pass' ? '✓' : '✗'}
                                  </span>
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                      <span className="text-sm font-medium text-gray-900">{check.name}</span>
                                      {check.status === 'fail' && check.issues > 0 && (
                                        <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">
                                          {check.issues} {check.issues === 1 ? 'issue' : 'issues'}
                                        </span>
                                      )}
                                      {check.status === 'pass' && (
                                        <span className="text-xs bg-green-100 text-green-600 px-2 py-0.5 rounded-full">No issues</span>
                                      )}
                                    </div>
                                    {check.details && (
                                      <p className="text-xs text-gray-500 mt-0.5">{check.details}</p>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                <div className="grid md:grid-cols-2 gap-6">
                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">✓ Strengths</h2>
                    <ul className="space-y-3">
                      {analysis.strengths.map((s, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                          <span className="text-green-500 mt-0.5 flex-shrink-0">✓</span>{s}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">✗ Weaknesses</h2>
                    <ul className="space-y-3">
                      {analysis.weaknesses.map((w, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                          <span className="text-red-500 mt-0.5 flex-shrink-0">✗</span>{w}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="bg-white rounded-xl shadow-md p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Actionable Suggestions</h2>
                  <ul className="space-y-3">
                    {analysis.suggestions.map((s, i) => (
                      <li key={i} className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg text-sm text-gray-700">
                        <span className="text-blue-600 font-bold flex-shrink-0">{i + 1}.</span>{s}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  {analysis.missing_keywords?.length > 0 && (
                    <div className="bg-white rounded-xl shadow-md p-6">
                      <h2 className="text-lg font-semibold text-gray-900 mb-3">Missing Keywords</h2>
                      <div className="flex flex-wrap gap-2">
                        {analysis.missing_keywords.map((k, i) => (
                          <span key={i} className="bg-red-50 text-red-600 px-3 py-1 rounded-full text-sm">{k}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {analysis.missing_sections?.length > 0 && (
                    <div className="bg-white rounded-xl shadow-md p-6">
                      <h2 className="text-lg font-semibold text-gray-900 mb-3">Missing Sections</h2>
                      <ul className="space-y-2">
                        {analysis.missing_sections.map((s, i) => (
                          <li key={i} className="text-sm text-gray-700 flex items-center gap-2">
                            <span className="text-yellow-500">!</span>{s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {/* ── TAILOR TAB ───────────────────────────────────────── */}
        {tab === 'tailor' && (
          <div className="space-y-6">
            {tailorRunning && (
              <AgentProgressPanel
                steps={TAILOR_STEPS}
                currentStep={tailorStep}
                running={tailorRunning}
                doneLabel="Tailored CV version saved"
              />
            )}

            {!tailorRunning && (
              <div className="bg-white rounded-xl shadow-md p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-1">Tailor CV to a Job</h2>
                <p className="text-gray-500 text-sm mb-1">
                  Three AI agents collaborate to rewrite your CV for this specific role:
                </p>
                <div className="flex flex-wrap gap-2 mb-6 text-xs">
                  <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full">💼 Job Analyst Agent</span>
                  <span className="text-gray-400 self-center">→</span>
                  <span className="bg-orange-50 text-orange-700 px-3 py-1 rounded-full">🔄 Gap Analyst Agent</span>
                  <span className="text-gray-400 self-center">→</span>
                  <span className="bg-green-50 text-green-700 px-3 py-1 rounded-full">✍️ CV Writer Agent</span>
                </div>

                {tailorDone && (
                  <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-4 text-sm">
                    ✓ Tailored CV version saved — see Versions below.
                  </div>
                )}

                <form onSubmit={startTailor} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Job Title</label>
                      <input
                        type="text"
                        value={jobTitle}
                        onChange={(e) => setJobTitle(e.target.value)}
                        placeholder="e.g. Senior Software Engineer"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
                      <input
                        type="text"
                        value={jobCompany}
                        onChange={(e) => setJobCompany(e.target.value)}
                        placeholder="e.g. Google"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Job Description <span className="text-red-500">*</span>
                    </label>
                    <textarea
                      value={jobDescription}
                      onChange={(e) => setJobDescription(e.target.value)}
                      rows={10}
                      required
                      placeholder="Paste the full job description here…"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none font-mono text-sm"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={!cv.is_parsed || !jobDescription.trim()}
                    className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 font-semibold"
                  >
                    {!cv.is_parsed ? 'CV not parsed yet' : 'Start Tailoring (3 Agents)'}
                  </button>
                </form>
              </div>
            )}

            {/* Previous versions */}
            {cv.versions?.length > 0 && (
              <div className="bg-white rounded-xl shadow-md p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  CV Versions ({cv.versions.length})
                </h2>
                <div className="space-y-3">
                  {cv.versions.map((v) => (
                    <div key={v.id} className="p-4 border border-gray-100 rounded-lg hover:border-gray-200 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <p className="font-medium text-sm text-gray-900">{v.title}</p>
                        <div className="flex items-center gap-2">
                          {v.ats_score != null && (
                            <span className="text-xs bg-blue-50 text-blue-600 px-2 py-1 rounded">ATS: {v.ats_score}</span>
                          )}
                          <span className={`text-xs px-2 py-1 rounded ${
                            v.version_type === 'job_tailored'
                              ? 'bg-green-50 text-green-700'
                              : 'bg-purple-50 text-purple-700'
                          }`}>
                            {v.version_type === 'job_tailored' ? '✍️ Job Tailored' : '⚡ ATS Optimised'}
                          </span>
                          {v.is_current && (
                            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">Current</span>
                          )}
                        </div>
                      </div>
                      {(v.keywords_added?.length ?? 0) > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {v.keywords_added!.slice(0, 5).map((k, i) => (
                            <span key={i} className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded">{k}</span>
                          ))}
                          {v.keywords_added!.length > 5 && (
                            <span className="text-xs text-gray-400">+{v.keywords_added!.length - 5} more</span>
                          )}
                        </div>
                      )}
                      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
                        <button
                          onClick={() => viewVersion(v.id)}
                          disabled={loadingVersion}
                          className="flex-1 bg-blue-600 text-white text-sm py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                        >
                          {loadingVersion ? 'Loading...' : 'View Details'}
                        </button>
                        <button
                          onClick={() => downloadPDF(v.id)}
                          disabled={downloadingPDF === v.id}
                          className="flex-1 border border-blue-600 text-blue-600 text-sm py-2 rounded-lg hover:bg-blue-50 disabled:opacity-50 transition-colors flex items-center justify-center gap-1"
                        >
                          {downloadingPDF === v.id ? (
                            <span className="animate-spin inline-block">⏳</span>
                          ) : (
                            <span>📥</span>
                          )}
                          {downloadingPDF === v.id ? 'Downloading...' : 'Download PDF'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Version Detail Modal */}
        {viewingVersion && viewingVersion.version && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
              {/* Modal Header */}
              <div className="p-6 border-b border-gray-200 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{viewingVersion.version.title}</h2>
                  <p className="text-sm text-gray-500">
                    Version {viewingVersion.version.version_number} · {viewingVersion.version.version_type}
                  </p>
                </div>
                <button
                  onClick={() => setViewingVersion(null)}
                  className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
                >
                  &times;
                </button>
              </div>

              {/* Modal Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">

                {/* Scores */}
                {(viewingVersion.version.ats_score || viewingVersion.version.overall_score) && (
                  <div className="flex gap-6 p-4 bg-blue-50 rounded-xl">
                    {viewingVersion.version.ats_score && (
                      <div className="text-center">
                        <p className="text-xs text-gray-500 mb-1">ATS Score</p>
                        <p className="text-3xl font-bold text-blue-600">{viewingVersion.version.ats_score}</p>
                      </div>
                    )}
                    {viewingVersion.version.overall_score && (
                      <div className="text-center">
                        <p className="text-xs text-gray-500 mb-1">Overall Score</p>
                        <p className="text-3xl font-bold text-purple-600">{viewingVersion.version.overall_score}</p>
                      </div>
                    )}
                    {viewingVersion.version.optimization_target && (
                      <div className="ml-auto text-right">
                        <p className="text-xs text-gray-500 mb-1">Tailored for</p>
                        <p className="text-sm font-semibold text-gray-700">{viewingVersion.version.optimization_target}</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Claude's full rewritten CV — displayed exactly as written */}
                {viewingVersion.version.optimized_text && (
                  <div>
                    <h3 className="font-semibold text-gray-700 text-sm uppercase tracking-wide mb-3">AI-Tailored CV</h3>
                    <pre className="whitespace-pre-wrap font-sans text-sm text-gray-800 bg-gray-50 border border-gray-200 rounded-xl p-6 leading-relaxed">
                      {viewingVersion.version.optimized_text}
                    </pre>
                  </div>
                )}

                {/* Changes Made */}
                {(viewingVersion.version.changes_made?.length ?? 0) > 0 && (
                  <div className="p-4 bg-yellow-50 rounded-xl border border-yellow-100">
                    <h3 className="font-semibold text-gray-900 mb-3">What Claude Changed</h3>
                    <ul className="space-y-2">
                      {viewingVersion.version.changes_made!.map((change, i) => (
                        <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                          <span className="text-yellow-600 mt-0.5 flex-shrink-0">→</span>{change}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Keywords Added */}
                {(viewingVersion.version.keywords_added?.length ?? 0) > 0 && (
                  <div className="p-4 bg-green-50 rounded-xl border border-green-100">
                    <h3 className="font-semibold text-gray-900 mb-3">Keywords Added for This Job</h3>
                    <div className="flex flex-wrap gap-2">
                      {viewingVersion.version.keywords_added!.map((k, i) => (
                        <span key={i} className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm font-medium">{k}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="p-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  onClick={() => setViewingVersion(null)}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium"
                >
                  Close
                </button>
                <button
                  onClick={() => downloadPDF(viewingVersion.version.id)}
                  disabled={downloadingPDF === viewingVersion.version.id}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {downloadingPDF === viewingVersion.version.id ? (
                    <span className="animate-spin inline-block">⏳</span>
                  ) : (
                    <span>📥</span>
                  )}
                  Download PDF
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
