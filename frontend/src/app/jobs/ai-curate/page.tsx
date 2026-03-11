'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

// Types
interface CV {
  id: string
  title: string
  original_filename: string
  file_type: string
  file_size: number
  has_data: boolean
  has_analysis: boolean
  uploaded_at: string
}

interface EducationItem {
  degree: string
  institution: string
  year: string
}

interface ExperienceItem {
  company: string
  role: string
  duration: string
  description: string
}

export default function AICuratePage() {
  return (
    <ProtectedRoute>
      <AICurate />
    </ProtectedRoute>
  )
}

function AICurate() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<'upload' | 'existing' | 'manual'>('upload')
  const [cvs, setCvs] = useState<CV[]>([])
  const [selectedCVId, setSelectedCVId] = useState<string>('')
  const [loadingCVs, setLoadingCVs] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  
  // CV upload state
  const [cvFile, setCvFile] = useState<File | null>(null)
  const [uploadingCV, setUploadingCV] = useState(false)
  const [uploadedCVId, setUploadedCVId] = useState<string>('')

  // Manual CV form state
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    location: '',
    job_title: '',
    years_experience: '',
    skills: '',
    summary: '',
    linkedin_url: '',
    github_url: '',
    website_url: '',
    save_as_cv: true,
    education: [] as EducationItem[],
    work_experience: [] as ExperienceItem[]
  })

  useEffect(() => {
    fetchCVs()
  }, [])

  // Helper to extract readable error message from backend response
  const extractError = (data: any, fallback: string): string => {
    if (!data) return fallback
    if (typeof data.message === 'string') return data.message
    if (typeof data.detail === 'string') return data.detail
    if (typeof data.error === 'string') return data.error
    return fallback
  }

  const fetchCVs = async () => {
    setLoadingCVs(true)
    try {
      const res = await apiFetch('/api/cv/')
      if (res.ok) {
        const data = await res.json()
        setCvs(Array.isArray(data) ? data : (data.results || []))
      } else if (res.status === 401) {
        setError('Session expired. Please log out and log back in.')
      }
    } finally {
      setLoadingCVs(false)
    }
  }

  const handleStartWithExisting = async () => {
    if (!selectedCVId) {
      setError('Please select a CV')
      return
    }

    setSubmitting(true)
    setError('')

    try {
      const res = await apiFetch('/api/jobs/workflow/start-curation/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          existing_cv_id: selectedCVId
        })
      })

      if (res.ok) {
        const data = await res.json()
        router.push(`/jobs/ai-matches?cv_id=${data.cv_id}`)
      } else {
        const errData = await res.json().catch(() => ({}))
        if (res.status === 401) {
          setError('Session expired. Please log out and log back in.')
        } else {
          setError(extractError(errData, 'Failed to start curation'))
        }
      }
    } catch (err: any) {
      setError(err.message || 'Network error. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Check file type
      const validTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
      if (!validTypes.includes(file.type)) {
        setError('Please upload a PDF or Word document')
        return
      }
      
      // Check file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setError('File size must be less than 10MB')
        return
      }
      
      setCvFile(file)
      setError('')
    }
  }

  const handleCVUpload = async () => {
    if (!cvFile) {
      setError('Please select a CV file to upload')
      return
    }

    setUploadingCV(true)
    setError('')

      try {
        const formData = new FormData()
        formData.append('file', cvFile)
        formData.append('title', cvFile.name.replace(/\.[^/.]+$/, '')) // Use filename without extension as title
        formData.append('is_temporary', 'true') // Mark as temporary for AI curation only

        const res = await apiFetch('/api/cv/upload/', {
          method: 'POST',
          body: formData
        })

      if (res.ok) {
        const data = await res.json()
        setUploadedCVId(data.id)
        setError('')
        await startCurationWithCV(data.id)
      } else {
        const errData = await res.json().catch(() => ({}))
        if (res.status === 401) {
          setError('Session expired. Please log out and log back in.')
        } else {
          setError(extractError(errData, 'Failed to upload CV'))
        }
      }
    } catch (err: any) {
      setError(err.message || 'Network error. Please try again.')
    } finally {
      setUploadingCV(false)
    }
  }

  const startCurationWithCV = async (cvId: string) => {
    setSubmitting(true)
    setError('')

    try {
      const res = await apiFetch('/api/jobs/workflow/start-curation/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          existing_cv_id: cvId
        })
      })

      if (res.ok) {
        const data = await res.json()
        router.push(`/jobs/ai-matches?cv_id=${data.cv_id}`)
      } else {
        const errData = await res.json().catch(() => ({}))
        if (res.status === 401) {
          setError('Session expired. Please log out and log back in.')
        } else if (res.status === 404) {
          setError('CV not found. Please re-upload your CV.')
        } else {
          setError(extractError(errData, 'Failed to start curation. Please try again.'))
        }
      }
    } catch (err: any) {
      setError(err.message || 'Network error. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleStartWithManual = async () => {
    // Validate required fields
    if (!formData.full_name || !formData.email || !formData.job_title || !formData.skills) {
      setError('Please fill in all required fields (Name, Email, Job Title, Skills)')
      return
    }

    setSubmitting(true)
    setError('')

    try {
      const res = await apiFetch('/api/jobs/workflow/start-curation/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: formData.full_name,
          email: formData.email,
          phone: formData.phone,
          location: formData.location,
          job_title: formData.job_title,
          years_experience: formData.years_experience ? parseInt(formData.years_experience) : 0,
          skills: formData.skills.split(',').map(s => s.trim()).filter(s => s),
          summary: formData.summary,
          linkedin_url: formData.linkedin_url,
          github_url: formData.github_url,
          website_url: formData.website_url,
          save_as_cv: formData.save_as_cv,
          education: formData.education,
          work_experience: formData.work_experience
        })
      })

      if (res.ok) {
        const data = await res.json()
        router.push(`/jobs/ai-matches?cv_id=${data.cv_id}`)
      } else {
        const errData = await res.json().catch(() => ({}))
        if (res.status === 401) {
          setError('Session expired. Please log out and log back in.')
        } else {
          setError(extractError(errData, 'Failed to create CV'))
        }
      }
    } catch (err: any) {
      setError(err.message || 'Network error. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const addEducation = () => {
    setFormData(prev => ({
      ...prev,
      education: [...prev.education, { degree: '', institution: '', year: '' }]
    }))
  }

  const removeEducation = (index: number) => {
    setFormData(prev => ({
      ...prev,
      education: prev.education.filter((_, i) => i !== index)
    }))
  }

  const updateEducation = (index: number, field: keyof EducationItem, value: string) => {
    setFormData(prev => ({
      ...prev,
      education: prev.education.map((item, i) => 
        i === index ? { ...item, [field]: value } : item
      )
    }))
  }

  const addExperience = () => {
    setFormData(prev => ({
      ...prev,
      work_experience: [...prev.work_experience, { company: '', role: '', duration: '', description: '' }]
    }))
  }

  const removeExperience = (index: number) => {
    setFormData(prev => ({
      ...prev,
      work_experience: prev.work_experience.filter((_, i) => i !== index)
    }))
  }

  const updateExperience = (index: number, field: keyof ExperienceItem, value: string) => {
    setFormData(prev => ({
      ...prev,
      work_experience: prev.work_experience.map((item, i) => 
        i === index ? { ...item, [field]: value } : item
      )
    }))
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <Link href="/jobs" className="text-gray-500 hover:text-gray-900 text-sm">
                ← Back to Jobs
              </Link>
              <h1 className="text-3xl font-bold text-gray-900 mt-2">AI Job Curation</h1>
              <p className="text-gray-600 mt-1">
                Choose how you want to curate jobs for your career
              </p>
            </div>
          </div>
        </div>
      </header>

        {/* Tab Navigation */}
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="bg-white rounded-lg shadow-sm p-2 inline-flex gap-2">
            <button
              onClick={() => setActiveTab('upload')}
              className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                activeTab === 'upload'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Upload CV
            </button>
            <button
              onClick={() => setActiveTab('existing')}
              className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                activeTab === 'existing'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Use Existing CV
            </button>
            <button
              onClick={() => setActiveTab('manual')}
              className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                activeTab === 'manual'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Enter CV Details
            </button>
          </div>

        {/* Error Message */}
        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Upload CV Tab */}
        {activeTab === 'upload' && (
          <div className="mt-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Upload Your CV</h2>
              <p className="text-gray-600 mb-6">
                Upload your CV document (PDF or Word) and AI will analyze it to find the best job matches for you.
              </p>

              {/* Upload Area */}
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-500 transition-colors">
                <input
                  type="file"
                  id="cv-upload"
                  accept=".pdf,.doc,.docx"
                  onChange={handleFileChange}
                  className="hidden"
                  disabled={uploadingCV || submitting}
                />
                <label
                  htmlFor="cv-upload"
                  className={`cursor-pointer ${uploadingCV || submitting ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <div className="text-5xl mb-4">📄</div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {cvFile ? cvFile.name : 'Click to upload or drag and drop'}
                  </h3>
                  <p className="text-gray-500 text-sm">
                    PDF or Word document (max 10MB)
                  </p>
                  {cvFile && (
                    <div className="mt-3 inline-flex items-center gap-2 bg-blue-50 text-blue-700 px-4 py-2 rounded-lg">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      {formatBytes(cvFile.size)}
                    </div>
                  )}
                </label>
              </div>

              {/* File Info */}
              {cvFile && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="bg-blue-100 p-2 rounded-lg">
                        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{cvFile.name}</p>
                        <p className="text-sm text-gray-500">{formatBytes(cvFile.size)}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        setCvFile(null)
                        setError('')
                      }}
                      className="text-red-600 hover:text-red-700"
                      disabled={uploadingCV || submitting}
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              )}

              {/* Upload Button */}
              <button
                onClick={handleCVUpload}
                disabled={!cvFile || uploadingCV || submitting}
                className="mt-6 w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {uploadingCV || submitting ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                    {uploadingCV ? 'Uploading...' : 'Processing...'}
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    Upload & Start AI Curation
                  </>
                )}
              </button>

              {/* Tips */}
              <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                <h4 className="font-semibold text-blue-900 mb-2">💡 Tips for better results</h4>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>• Ensure your CV includes your skills, experience, and education</li>
                  <li>• Use a clear, well-structured format</li>
                  <li>• Include keywords relevant to your target job</li>
                  <li>• The AI will analyze your CV and find matching jobs</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Existing CV Tab */}
        {activeTab === 'existing' && (
          <div className="mt-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Select Your CV</h2>
              
              {loadingCVs ? (
                <div className="flex justify-center py-12">
                  <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
                </div>
              ) : cvs.length === 0 ? (
                <div className="text-center py-12">
                  <div className="text-5xl mb-4">📄</div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">No CVs Available</h3>
                  <p className="text-gray-500 mb-4">
                    You don't have any CVs uploaded yet. You can either upload one in the CV Builder section or use the manual entry option.
                  </p>
                  <div className="flex gap-3 justify-center">
                    <Link
                      href="/cv"
                      className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
                    >
                      Go to CV Builder
                    </Link>
                    <button
                      onClick={() => setActiveTab('manual')}
                      className="inline-block border border-blue-600 text-blue-600 px-6 py-2 rounded-lg hover:bg-blue-50"
                    >
                      Enter Details Manually
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {cvs.map((cv) => (
                    <div
                      key={cv.id}
                      className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                        selectedCVId === cv.id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => setSelectedCVId(cv.id)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900">{cv.title}</h3>
                          <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                            <span>{formatBytes(cv.file_size)}</span>
                            <span>{new Date(cv.uploaded_at).toLocaleDateString()}</span>
                            {cv.has_data && (
                              <span className="text-green-600">✓ Parsed</span>
                            )}
                          </div>
                        </div>
                        <div className="ml-4">
                          <input
                            type="radio"
                            name="cv-selection"
                            checked={selectedCVId === cv.id}
                            onChange={() => setSelectedCVId(cv.id)}
                            className="w-5 h-5 text-blue-600"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={handleStartWithExisting}
                disabled={!selectedCVId || submitting || loadingCVs || cvs.length === 0}
                className="mt-6 w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {submitting ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                    Processing...
                  </>
                ) : (
                  'Start AI Curation'
                )}
              </button>
            </div>
          </div>
        )}

        {/* Manual CV Tab */}
        {activeTab === 'manual' && (
          <div className="mt-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-6">Enter Your CV Details</h2>
              
              <div className="space-y-6">
                {/* Personal Info */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Full Name *
                    </label>
                    <input
                      type="text"
                      value={formData.full_name}
                      onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="John Doe"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email *
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="john@example.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Phone
                    </label>
                    <input
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="+254 712 345 678"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Location
                    </label>
                    <input
                      type="text"
                      value={formData.location}
                      onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Nairobi, Kenya"
                    />
                  </div>
                </div>

                {/* Job Target */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Target Job Title *
                    </label>
                    <input
                      type="text"
                      value={formData.job_title}
                      onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Software Engineer"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Years of Experience
                    </label>
                    <input
                      type="number"
                      value={formData.years_experience}
                      onChange={(e) => setFormData({ ...formData, years_experience: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="5"
                      min="0"
                    />
                  </div>
                </div>

                {/* Skills */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Skills (comma-separated) *
                  </label>
                  <textarea
                    value={formData.skills}
                    onChange={(e) => setFormData({ ...formData, skills: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={2}
                    placeholder="Python, Django, React, JavaScript, AWS, Docker"
                  />
                </div>

                {/* Summary */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Professional Summary
                  </label>
                  <textarea
                    value={formData.summary}
                    onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={4}
                    placeholder="Experienced software engineer with 5+ years of experience building scalable web applications..."
                  />
                </div>

                {/* Social Links */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      LinkedIn URL
                    </label>
                    <input
                      type="url"
                      value={formData.linkedin_url}
                      onChange={(e) => setFormData({ ...formData, linkedin_url: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="https://linkedin.com/in/username"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      GitHub URL
                    </label>
                    <input
                      type="url"
                      value={formData.github_url}
                      onChange={(e) => setFormData({ ...formData, github_url: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="https://github.com/username"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Website/Portfolio
                    </label>
                    <input
                      type="url"
                      value={formData.website_url}
                      onChange={(e) => setFormData({ ...formData, website_url: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="https://yourwebsite.com"
                    />
                  </div>
                </div>

                {/* Education */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Education
                    </label>
                    <button
                      type="button"
                      onClick={addEducation}
                      className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                    >
                      + Add Education
                    </button>
                  </div>
                  {formData.education.map((edu, index) => (
                    <div key={index} className="mb-3 p-4 bg-gray-50 rounded-lg">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <input
                          type="text"
                          value={edu.degree}
                          onChange={(e) => updateEducation(index, 'degree', e.target.value)}
                          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          placeholder="Degree (e.g., BS Computer Science)"
                        />
                        <input
                          type="text"
                          value={edu.institution}
                          onChange={(e) => updateEducation(index, 'institution', e.target.value)}
                          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          placeholder="Institution"
                        />
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={edu.year}
                            onChange={(e) => updateEducation(index, 'year', e.target.value)}
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Year"
                          />
                          <button
                            type="button"
                            onClick={() => removeEducation(index)}
                            className="px-3 py-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Work Experience */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Work Experience
                    </label>
                    <button
                      type="button"
                      onClick={addExperience}
                      className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                    >
                      + Add Experience
                    </button>
                  </div>
                  {formData.work_experience.map((exp, index) => (
                    <div key={index} className="mb-3 p-4 bg-gray-50 rounded-lg">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-2">
                        <input
                          type="text"
                          value={exp.company}
                          onChange={(e) => updateExperience(index, 'company', e.target.value)}
                          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          placeholder="Company"
                        />
                        <input
                          type="text"
                          value={exp.role}
                          onChange={(e) => updateExperience(index, 'role', e.target.value)}
                          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          placeholder="Role"
                        />
                      </div>
                      <input
                        type="text"
                        value={exp.duration}
                        onChange={(e) => updateExperience(index, 'duration', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-2"
                        placeholder="Duration (e.g., 2022-Present, 2020-2022)"
                      />
                      <textarea
                        value={exp.description}
                        onChange={(e) => updateExperience(index, 'description', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        rows={2}
                        placeholder="Description of responsibilities and achievements..."
                      />
                      <button
                        type="button"
                        onClick={() => removeExperience(index)}
                        className="mt-2 text-red-600 hover:text-red-700 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>

                {/* Save Option */}
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="save-as-cv"
                    checked={formData.save_as_cv}
                    onChange={(e) => setFormData({ ...formData, save_as_cv: e.target.checked })}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <label htmlFor="save-as-cv" className="text-sm text-gray-700">
                    Save this CV for future use
                  </label>
                </div>

                <button
                  onClick={handleStartWithManual}
                  disabled={submitting}
                  className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {submitting ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                      Processing...
                    </>
                  ) : (
                    'Start AI Curation'
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
