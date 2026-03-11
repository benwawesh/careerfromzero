'use client'

import { useState, useEffect, useCallback } from 'react'
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
  is_featured?: boolean
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
  jobwebkenya: 'bg-lime-100 text-lime-700',
  ngojobs: 'bg-green-100 text-green-700',
  corporatestaffing: 'bg-slate-100 text-slate-700',
  nationkenya: 'bg-red-100 text-red-700',
  jobberman: 'bg-orange-100 text-orange-700',
  career24: 'bg-cyan-100 text-cyan-600',
  indeedrss: 'bg-indigo-100 text-indigo-600',
  weworkremotely: 'bg-emerald-100 text-emerald-700',
}

const SOURCE_NAMES: Record<string, string> = {
  linkedin: 'LinkedIn', indeed: 'Indeed', glassdoor: 'Glassdoor',
  ziprecruiter: 'ZipRecruiter', adzuna: 'Adzuna',
  remotive: 'Remotive', arbeitnow: 'Arbeitnow', jobicy: 'Jobicy',
  remoteok: 'RemoteOK', themuse: 'The Muse',
  brightermonday: 'BrighterMonday', fuzu: 'Fuzu',
  kenyajob: 'KenyaJob', myjobmag: 'MyJobMag',
  jobwebkenya: 'Jobwebkenya', ngojobs: 'NGO Jobs',
  corporatestaffing: 'Corporate Staffing', nationkenya: 'Nation Kenya',
  jobberman: 'Jobberman', career24: 'Career24',
  indeedrss: 'Indeed RSS', weworkremotely: 'We Work Remotely',
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
}

function isNewJob(postedDate?: string): boolean {
  if (!postedDate) return false
  const jobDate = new Date(postedDate)
  const threeDaysAgo = new Date()
  threeDaysAgo.setDate(threeDaysAgo.getDate() - 3)
  return jobDate >= threeDaysAgo
}

function formatSalary(job: Job): string {
  if (job.salary_range) return job.salary_range
  if (job.salary_min && job.salary_max) {
    return `$${job.salary_min.toLocaleString()} - $${job.salary_max.toLocaleString()}`
  }
  if (job.salary_min) return `$${job.salary_min.toLocaleString()}+`
  if (job.salary_max) return `Up to $${job.salary_max.toLocaleString()}`
  return 'Salary not specified'
}

// Check if job is Kenyan (local)
function isKenyanJob(job: Job): boolean {
  const kenyanKeywords = ['kenya', 'nairobi', 'mombasa', 'kisumu', 'nakuru', 'eldoret', 'thika']
  const locationLower = job.location.toLowerCase()
  const sourceLower = job.source.toLowerCase()
  
  return kenyanKeywords.some(keyword => 
    locationLower.includes(keyword) || sourceLower.includes(keyword)
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function JobsPage() {
  return (
    <ProtectedRoute>
      <JobsMarketplace />
    </ProtectedRoute>
  )
}

function JobsMarketplace() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  
  // Pagination State
  const [currentPage, setCurrentPage] = useState(1)
  const ITEMS_PER_PAGE = 100
  
  // Global Search State
  const [keyword, setKeyword] = useState('')
  const [jobFunction, setJobFunction] = useState('')
  const [industry, setIndustry] = useState('')
  const [location, setLocation] = useState('')
  const [experience, setExperience] = useState('')
  const [countryFilter, setCountryFilter] = useState('all') // 'all', 'kenya', 'international'
  
  // Filter Sidebar State
  const [searchWithin, setSearchWithin] = useState('')
  const [jobTypes, setJobTypes] = useState<Set<string>>(new Set())
  const [filterLocations, setFilterLocations] = useState<Set<string>>(new Set())
  const [salaryMin, setSalaryMin] = useState('')
  const [salaryMax, setSalaryMax] = useState('')
  const [expLevels, setExpLevels] = useState<Set<string>>(new Set())
  const [datePosted, setDatePosted] = useState('')
  const [orderBy, setOrderBy] = useState('latest')
  
  // Expanded filter sections
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['job_types']))

  useEffect(() => {
    fetchJobs()
    fetchSavedIds()
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

  async function fetchSavedIds() {
    try {
      const r = await apiFetch('/api/jobs/jobs/saved_ids/')
      if (r.ok) { 
        const d = await r.json(); 
        setSavedIds(new Set(d.saved_ids || [])) 
      }
    } catch { /* non-critical */ }
  }

  function toggleJobType(type: string) {
    setJobTypes(prev => {
      const next = new Set(prev)
      if (next.has(type)) next.delete(type)
      else next.add(type)
      return next
    })
  }

  function toggleFilterLocation(loc: string) {
    setFilterLocations(prev => {
      const next = new Set(prev)
      if (next.has(loc)) next.delete(loc)
      else next.add(loc)
      return next
    })
  }

  function toggleExpLevel(level: string) {
    setExpLevels(prev => {
      const next = new Set(prev)
      if (next.has(level)) next.delete(level)
      else next.add(level)
      return next
    })
  }

  function toggleSection(section: string) {
    setExpandedSections(prev => {
      const next = new Set(prev)
      if (next.has(section)) next.delete(section)
      else next.add(section)
      return next
    })
  }

  function handleSearch() {
    // Will implement full search with backend filters
    console.log('Search with:', { keyword, jobFunction, industry, location, experience })
  }

  function resetFilters() {
    setSearchWithin('')
    setJobTypes(new Set())
    setFilterLocations(new Set())
    setSalaryMin('')
    setSalaryMax('')
    setExpLevels(new Set())
    setDatePosted('')
    setOrderBy('latest')
  }

  const displayed = useCallback(() => {
    let list = [...jobs]
    
    // Country Filter: Separate Kenyan and International jobs
    if (countryFilter === 'kenya') {
      list = list.filter(job => isKenyanJob(job))
    } else if (countryFilter === 'international') {
      list = list.filter(job => !isKenyanJob(job))
    }
    
    // Apply sidebar filters
    if (searchWithin) {
      const q = searchWithin.toLowerCase()
      list = list.filter(j =>
        j.title.toLowerCase().includes(q) ||
        j.company.toLowerCase().includes(q) ||
        j.description.toLowerCase().includes(q)
      )
    }
    
    if (jobTypes.size > 0) {
      list = list.filter(j => j.job_type && jobTypes.has(j.job_type))
    }
    
    if (filterLocations.size > 0) {
      list = list.filter(j => j.location && [...filterLocations].some(loc => 
        j.location!.toLowerCase().includes(loc.toLowerCase())
      ))
    }
    
    if (salaryMin) {
      list = list.filter(j => (j.salary_min || 0) >= parseInt(salaryMin))
    }
    
    if (salaryMax) {
      list = list.filter(j => (j.salary_max || Infinity) <= parseInt(salaryMax))
    }
    
    if (expLevels.size > 0) {
      list = list.filter(j => j.experience_level && expLevels.has(j.experience_level))
    }
    
    if (datePosted) {
      const now = new Date()
      if (datePosted === 'today') {
        list = list.filter(j => {
          if (!j.posted_date) return false
          const posted = new Date(j.posted_date)
          return posted.toDateString() === now.toDateString()
        })
      } else if (datePosted === 'week') {
        const weekAgo = new Date()
        weekAgo.setDate(weekAgo.getDate() - 7)
        list = list.filter(j => j.posted_date && new Date(j.posted_date) >= weekAgo)
      } else if (datePosted === 'month') {
        const monthAgo = new Date()
        monthAgo.setMonth(monthAgo.getMonth() - 1)
        list = list.filter(j => j.posted_date && new Date(j.posted_date) >= monthAgo)
      }
    }
    
    // Prioritize Kenyan jobs first when country filter is 'all'
    if (countryFilter === 'all') {
      list.sort((a, b) => {
        const aIsKenyan = isKenyanJob(a) ? 0 : 1
        const bIsKenyan = isKenyanJob(b) ? 0 : 1
        return aIsKenyan - bIsKenyan
      })
    }
    
    // Apply ordering
    if (orderBy === 'latest') {
      list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    } else if (orderBy === 'featured') {
      list.sort((a, b) => Number(b.is_featured || 0) - Number(a.is_featured || 0))
    } else if (orderBy === 'popular') {
      list.sort((a, b) => (b.view_count || 0) - (a.view_count || 0))
    }
    
    return list
  }, [jobs, searchWithin, jobTypes, filterLocations, salaryMin, salaryMax, expLevels, datePosted, orderBy, countryFilter])()

  // Pagination logic
  const totalPages = Math.ceil(displayed.length / ITEMS_PER_PAGE)
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
  const endIndex = startIndex + ITEMS_PER_PAGE
  const paginatedJobs = displayed.slice(startIndex, endIndex)

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [searchWithin, jobTypes, filterLocations, salaryMin, salaryMax, expLevels, datePosted, orderBy, countryFilter])

  // Count Kenyan vs International jobs
  const kenyanJobCount = jobs.filter(isKenyanJob).length
  const internationalJobCount = jobs.length - kenyanJobCount

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Global Search Header ── */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Keyword Input */}
            <div className="flex-1 min-w-48">
              <input
                type="text"
                placeholder="Job title, keywords, or company..."
                value={keyword}
                onChange={e => setKeyword(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            {/* Job Functions Dropdown */}
            <select
              value={jobFunction}
              onChange={e => setJobFunction(e.target.value)}
              className="px-4 py-2.5 border border-gray-300 rounded-lg text-sm bg-white min-w-32"
            >
              <option value="">Job Functions</option>
              <option value="engineering">Engineering</option>
              <option value="design">Design</option>
              <option value="marketing">Marketing</option>
              <option value="sales">Sales</option>
              <option value="finance">Finance</option>
              <option value="operations">Operations</option>
            </select>
            
            {/* Industries Dropdown */}
            <select
              value={industry}
              onChange={e => setIndustry(e.target.value)}
              className="px-4 py-2.5 border border-gray-300 rounded-lg text-sm bg-white min-w-32"
            >
              <option value="">Industries</option>
              <option value="technology">Technology</option>
              <option value="finance">Finance</option>
              <option value="healthcare">Healthcare</option>
              <option value="education">Education</option>
              <option value="retail">Retail</option>
            </select>
            
            {/* Locations Dropdown */}
            <select
              value={location}
              onChange={e => setLocation(e.target.value)}
              className="px-4 py-2.5 border border-gray-300 rounded-lg text-sm bg-white min-w-32"
            >
              <option value="">Locations</option>
              <option value="remote">Remote</option>
              <option value="nairobi">Nairobi</option>
              <option value="mombasa">Mombasa</option>
              <option value="kisumu">Kisumu</option>
            </select>
            
            {/* Experience Level Dropdown */}
            <select
              value={experience}
              onChange={e => setExperience(e.target.value)}
              className="px-4 py-2.5 border border-gray-300 rounded-lg text-sm bg-white min-w-32"
            >
              <option value="">Experience</option>
              <option value="entry">Entry Level</option>
              <option value="mid">Mid Level</option>
              <option value="senior">Senior Level</option>
              <option value="lead">Lead/Manager</option>
            </select>
            
            {/* Search Button */}
            <button
              onClick={handleSearch}
              className="px-6 py-2.5 bg-red-700 text-white text-sm font-medium rounded-lg hover:bg-red-800 transition-colors min-w-32"
            >
              Search
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Content ── */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-6">
          {/* ── Left: Job Cards Feed (70%) ── */}
          <div className="flex-1 space-y-4">
            {/* AI Curation CTA */}
            <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl border border-gray-200 p-4 mb-4 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-lg mb-1">✨ AI Job Curation</h3>
                  <p className="text-blue-50 text-sm">Let AI find the perfect jobs for you based on your CV</p>
                </div>
                <Link
                  href="/jobs/ai-curate"
                  className="px-4 py-2 bg-white text-blue-600 rounded-lg font-semibold hover:bg-blue-50 transition-colors"
                >
                  Start Curation
                </Link>
              </div>
            </div>

            {/* Country Filter */}
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium text-gray-700">Filter by Country:</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setCountryFilter('all')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        countryFilter === 'all'
                          ? 'bg-red-700 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      All ({jobs.length.toLocaleString()})
                    </button>
                    <button
                      onClick={() => setCountryFilter('kenya')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        countryFilter === 'kenya'
                          ? 'bg-red-700 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      🇰🇪 Kenya ({kenyanJobCount.toLocaleString()})
                    </button>
                    <button
                      onClick={() => setCountryFilter('international')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        countryFilter === 'international'
                          ? 'bg-red-700 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      🌍 International ({internationalJobCount.toLocaleString()})
                    </button>
                  </div>
                </div>
              </div>
              {countryFilter === 'all' && (
                <p className="text-xs text-gray-500 mt-2">
                  ⭐ Kenyan jobs are shown first for better local visibility
                </p>
              )}
            </div>

            {/* Results Count */}
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-500">
                {loading ? 'Loading...' : `${displayed.length} job${displayed.length !== 1 ? 's' : ''} found`}
                {!loading && displayed.length > 0 && (
                  <span className="ml-2 text-gray-400">
                    (Page {currentPage} of {totalPages}, showing {startIndex + 1}-{Math.min(endIndex, displayed.length)})
                  </span>
                )}
              </p>
              <div className="flex items-center gap-2 text-sm">
                <Link
                  href="/jobs/ai-matches"
                  className="text-blue-600 hover:underline font-medium"
                >
                  View AI-Curated Jobs →
                </Link>
              </div>
            </div>
            
            {loading ? (
              <div className="flex justify-center py-20">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-red-700" />
              </div>
            ) : displayed.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                <p className="text-4xl mb-3">🔍</p>
                <h3 className="text-lg font-semibold text-gray-900 mb-1">No jobs found</h3>
                <p className="text-gray-500 text-sm">
                  Try adjusting your search or filters
                </p>
              </div>
            ) : (
              <>
                <div className="space-y-3">
                  {paginatedJobs.map(job => (
                    <JobCard
                      key={job.id}
                      job={job}
                      isSaved={savedIds.has(job.id)}
                    />
                  ))}
                </div>
                
                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="mt-6 bg-white rounded-xl border border-gray-200 p-4">
                    <div className="flex items-center justify-between">
                      {/* Previous Button */}
                      <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        ← Previous
                      </button>
                      
                      {/* Page Numbers */}
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setCurrentPage(1)}
                          className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                            currentPage === 1 
                              ? 'bg-red-700 text-white' 
                              : 'border border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          1
                        </button>
                        
                        {totalPages > 5 && currentPage > 3 && (
                          <span className="px-2 text-gray-400">...</span>
                        )}
                        
                        {Array.from({ length: Math.min(3, totalPages - 2) }, (_, i) => {
                          const pageNum = currentPage > 3 
                            ? currentPage + i - 1 
                            : i + 2
                          if (pageNum <= 0 || pageNum >= totalPages) return null
                          return (
                            <button
                              key={pageNum}
                              onClick={() => setCurrentPage(pageNum)}
                              className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                                currentPage === pageNum 
                                  ? 'bg-red-700 text-white' 
                                  : 'border border-gray-300 hover:bg-gray-50'
                              }`}
                            >
                              {pageNum}
                            </button>
                          )
                        })}
                        
                        {totalPages > 5 && currentPage < totalPages - 2 && (
                          <span className="px-2 text-gray-400">...</span>
                        )}
                        
                        {totalPages > 1 && (
                          <button
                            onClick={() =>                              setCurrentPage(totalPages)}
                              className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                                currentPage === totalPages 
                                  ? 'bg-red-700 text-white' 
                                  : 'border border-gray-300 hover:bg-gray-50'
                              }`}
                            >
                              {totalPages}
                            </button>
                        )}
                      </div>
                      
                      {/* Next Button */}
                      <button
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Next →
                      </button>
                    </div>
                    
                    {/* Jump to Page */}
                    {totalPages > 10 && (
                      <div className="mt-3 flex items-center justify-center gap-2">
                        <span className="text-sm text-gray-500">Jump to page:</span>
                        <input
                          type="number"
                          min="1"
                          max={totalPages}
                          value={currentPage}
                          onChange={(e) => {
                            const page = parseInt(e.target.value)
                            if (page >= 1 && page <= totalPages) {
                              setCurrentPage(page)
                            }
                          }}
                          className="w-20 px-3 py-1.5 text-sm border border-gray-300 rounded-lg text-center"
                        />
                        <span className="text-sm text-gray-500">of {totalPages}</span>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          {/* ── Right: Filter Sidebar (30%) ── */}
          <aside className="w-80 flex-shrink-0 space-y-4">
            {/* Search Within Results */}
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <input
                type="text"
                placeholder="Search within results..."
                value={searchWithin}
                onChange={e => setSearchWithin(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Job Types */}
            <FilterSection
              title="Job Types"
              isOpen={expandedSections.has('job_types')}
              onToggle={() => toggleSection('job_types')}
            >
              {[
                { id: 'full_time', label: 'Full-time' },
                { id: 'remote', label: 'Remote' },
                { id: 'contract', label: 'Contract' },
                { id: 'part_time', label: 'Part-time' },
                { id: 'internship', label: 'Internship' },
                { id: 'freelance', label: 'Freelance' },
              ].map(({ id, label }) => (
                <label key={id} className="flex items-center gap-2 py-1.5 cursor-pointer hover:bg-gray-50 px-2 rounded">
                  <input
                    type="checkbox"
                    checked={jobTypes.has(id)}
                    onChange={() => toggleJobType(id)}
                    className="w-4 h-4 rounded border-gray-300 text-red-700 focus:ring-red-500"
                  />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
            </FilterSection>

            {/* Locations */}
            <FilterSection
              title="Locations"
              isOpen={expandedSections.has('locations')}
              onToggle={() => toggleSection('locations')}
            >
              {[
                { id: 'Nairobi', label: 'Nairobi' },
                { id: 'Mombasa', label: 'Mombasa' },
                { id: 'Kisumu', label: 'Kisumu' },
                { id: 'Remote', label: 'Remote' },
                { id: 'Kenya', label: 'Kenya (Any)' },
              ].map(({ id, label }) => (
                <label key={id} className="flex items-center gap-2 py-1.5 cursor-pointer hover:bg-gray-50 px-2 rounded">
                  <input
                    type="checkbox"
                    checked={filterLocations.has(id)}
                    onChange={() => toggleFilterLocation(id)}
                    className="w-4 h-4 rounded border-gray-300 text-red-700 focus:ring-red-500"
                  />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
            </FilterSection>

            {/* Salary Range */}
            <FilterSection
              title="Salary Range"
              isOpen={expandedSections.has('salary')}
              onToggle={() => toggleSection('salary')}
            >
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Min Salary</label>
                  <input
                    type="number"
                    placeholder="e.g., 50000"
                    value={salaryMin}
                    onChange={e => setSalaryMin(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Max Salary</label>
                  <input
                    type="number"
                    placeholder="e.g., 150000"
                    value={salaryMax}
                    onChange={e => setSalaryMax(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>
            </FilterSection>

            {/* Experience Level */}
            <FilterSection
              title="Experience Level"
              isOpen={expandedSections.has('experience')}
              onToggle={() => toggleSection('experience')}
            >
              {[
                { id: 'entry_level', label: 'Entry Level' },
                { id: 'mid_level', label: 'Mid Level' },
                { id: 'senior_level', label: 'Senior Level' },
                { id: 'lead', label: 'Lead/Manager' },
              ].map(({ id, label }) => (
                <label key={id} className="flex items-center gap-2 py-1.5 cursor-pointer hover:bg-gray-50 px-2 rounded">
                  <input
                    type="checkbox"
                    checked={expLevels.has(id)}
                    onChange={() => toggleExpLevel(id)}
                    className="w-4 h-4 rounded border-gray-300 text-red-700 focus:ring-red-500"
                  />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
            </FilterSection>

            {/* Date Posted */}
            <FilterSection
              title="Date Posted"
              isOpen={expandedSections.has('date_posted')}
              onToggle={() => toggleSection('date_posted')}
            >
              {[
                { id: 'today', label: 'Today' },
                { id: 'week', label: 'Past Week' },
                { id: 'month', label: 'Past Month' },
              ].map(({ id, label }) => (
                <label key={id} className="flex items-center gap-2 py-1.5 cursor-pointer hover:bg-gray-50 px-2 rounded">
                  <input
                    type="radio"
                    name="date_posted"
                    checked={datePosted === id}
                    onChange={() => setDatePosted(id)}
                    className="w-4 h-4 text-red-700 focus:ring-red-500"
                  />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
              {datePosted && (
                <button
                  onClick={() => setDatePosted('')}
                  className="text-xs text-blue-600 hover:underline mt-2"
                >
                  Clear date filter
                </button>
              )}
            </FilterSection>

            {/* Sort By */}
            <FilterSection
              title="Sort By"
              isOpen={expandedSections.has('sort')}
              onToggle={() => toggleSection('sort')}
            >
              {[
                { id: 'latest', label: 'Latest First' },
                { id: 'featured', label: 'Featured First' },
                { id: 'popular', label: 'Most Popular' },
              ].map(({ id, label }) => (
                <label key={id} className="flex items-center gap-2 py-1.5 cursor-pointer hover:bg-gray-50 px-2 rounded">
                  <input
                    type="radio"
                    name="order_by"
                    checked={orderBy === id}
                    onChange={() => setOrderBy(id)}
                    className="w-4 h-4 text-red-700 focus:ring-red-500"
                  />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
            </FilterSection>

            {/* Reset Filters */}
            <button
              onClick={resetFilters}
              className="w-full px-4 py-2.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors"
            >
              Reset All Filters
            </button>
          </aside>
        </div>
      </div>
    </div>
  )
}

// ─── Components ─────────────────────────────────────────────────────────────

function JobCard({ job, isSaved }: { job: Job; isSaved: boolean }) {
  const [saved, setSaved] = useState(isSaved)

  async function toggleSave() {
    try {
      const r = await apiFetch(`/api/jobs/jobs/${job.id}/save/`, {
        method: saved ? 'DELETE' : 'POST'
      })
      if (r.ok) {
        setSaved(!saved)
      }
    } catch (e) {
      console.error('Failed to toggle save:', e)
    }
  }

  return (
    <Link href={`/jobs/${job.id}`} className="block">
      <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-red-300 transition-all cursor-pointer">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-1 hover:text-red-700 transition-colors">{job.title}</h3>
            <p className="text-sm text-gray-600">{job.company}</p>
          </div>
          <button
            onClick={(e) => {
              e.preventDefault()
              toggleSave()
            }}
            className={`ml-3 p-2 rounded-lg transition-colors ${
              saved ? 'text-yellow-500 hover:bg-yellow-50' : 'text-gray-400 hover:bg-gray-100'
            }`}
          >
            <svg className="w-5 h-5" fill={saved ? 'currentColor' : 'none'} viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700">
            {job.location}
          </span>
          {job.job_type && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700">
              {job.job_type.replace('_', ' ')}
            </span>
          )}
          {job.source && SOURCE_COLORS[job.source] && (
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium ${SOURCE_COLORS[job.source]}`}>
              {SOURCE_NAMES[job.source] || job.source}
            </span>
          )}
        </div>

        <p className="text-sm text-gray-600 mb-3 line-clamp-2">
          {job.description ? stripHtml(job.description) : 'No description available. Click to view details.'}
        </p>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {job.salary_range && (
              <span className="text-sm text-gray-700 font-medium">
                {job.salary_range}
              </span>
            )}
            {!job.salary_range && job.salary_min && (
              <span className="text-sm text-gray-700 font-medium">
                ${job.salary_min.toLocaleString()}+
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-red-700 font-medium hover:text-red-800">
              View Details →
            </span>
          </div>
        </div>

        {job.posted_date && isNewJob(job.posted_date) && (
          <div className="mt-3">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-yellow-50 text-yellow-700">
              🔥 New
            </span>
          </div>
        )}
      </div>
    </Link>
  )
}

function FilterSection({ title, isOpen, onToggle, children }: {
  title: string
  isOpen: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <span className="text-sm font-medium text-gray-900">{title}</span>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="px-4 py-3 space-y-2">
          {children}
        </div>
      )}
    </div>
  )
}
