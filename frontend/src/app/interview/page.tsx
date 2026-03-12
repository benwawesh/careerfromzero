'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

export default function InterviewSetupPage() {
  return (
    <ProtectedRoute>
      <InterviewSetup />
    </ProtectedRoute>
  )
}

function InterviewSetup() {
  const router = useRouter()

  const [goalType, setGoalType] = useState<'job_posting' | 'career_path'>('career_path')
  const [jobDescription, setJobDescription] = useState('')
  const [careerPath, setCareerPath] = useState('')
  const [experienceLevel, setExperienceLevel] = useState('mid')
  const [interviewType, setInterviewType] = useState<'behavioural' | 'technical' | 'mixed'>('mixed')
  const [mode, setMode] = useState<'text' | 'voice'>('text')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const experienceLevels = [
    { value: 'junior', label: 'Junior / Entry Level' },
    { value: 'mid', label: 'Mid Level' },
    { value: 'senior', label: 'Senior' },
    { value: 'manager', label: 'Managerial / Team Lead' },
    { value: 'director', label: 'Director / Executive' },
  ]

  const interviewTypes = [
    {
      value: 'behavioural' as const,
      label: 'HR / Behavioural',
      description: 'Situational questions and soft skills',
      icon: '🤝',
    },
    {
      value: 'technical' as const,
      label: 'Technical',
      description: 'Role-specific knowledge and skills',
      icon: '💻',
    },
    {
      value: 'mixed' as const,
      label: 'Mixed',
      description: 'Both behavioural and technical',
      icon: '🔀',
    },
  ]

  const modes = [
    { value: 'text' as const, label: 'Text Only', icon: '⌨️', description: 'Type your answers' },
    { value: 'voice' as const, label: 'Voice + Text', icon: '🎤', description: 'Speak and type your answers' },
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    const careerGoal = goalType === 'job_posting' ? jobDescription : careerPath
    if (!careerGoal.trim()) {
      setError(goalType === 'job_posting' ? 'Please paste a job description.' : 'Please enter a career path.')
      return
    }

    setLoading(true)
    try {
      const res = await apiFetch('/api/interview/sessions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          career_goal: careerGoal.trim(),
          experience_level: experienceLevel,
          interview_type: interviewType,
          mode,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        router.push(`/interview/${data.id}`)
      } else {
        const data = await res.json().catch(() => ({}))
        setError(data.error || data.detail || 'Failed to create interview session. Please try again.')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Interview Simulator</h1>
            <p className="text-sm text-gray-500">Practice with Alex, your AI interview coach</p>
          </div>
          <Link href="/dashboard" className="text-gray-500 hover:text-gray-700 text-sm font-medium">
            ← Dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Intro banner */}
        <div className="bg-gradient-to-br from-purple-600 to-indigo-700 rounded-2xl shadow-lg p-6 mb-8 text-white">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center text-3xl flex-shrink-0">
              👤
            </div>
            <div>
              <p className="font-semibold text-lg">Hi, I'm Alex — your AI Interview Coach</p>
              <p className="text-purple-100 text-sm mt-1">
                I'll guide you through a full interview process, give you real-time feedback, and help you
                land that job. Let's set up your session.
              </p>
            </div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Step 1: Goal */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">
              1. What are you interviewing for?
            </h2>
            <div className="space-y-3">
              <label className={`flex items-start gap-3 p-4 rounded-xl border-2 cursor-pointer transition-all ${
                goalType === 'job_posting' ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-gray-300'
              }`}>
                <input
                  type="radio"
                  name="goalType"
                  value="job_posting"
                  checked={goalType === 'job_posting'}
                  onChange={() => setGoalType('job_posting')}
                  className="mt-0.5 text-purple-600 focus:ring-purple-500"
                />
                <div>
                  <span className="font-medium text-gray-900">A specific job posting</span>
                  <p className="text-sm text-gray-500">Paste the job description for a tailored interview</p>
                </div>
              </label>

              <label className={`flex items-start gap-3 p-4 rounded-xl border-2 cursor-pointer transition-all ${
                goalType === 'career_path' ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-gray-300'
              }`}>
                <input
                  type="radio"
                  name="goalType"
                  value="career_path"
                  checked={goalType === 'career_path'}
                  onChange={() => setGoalType('career_path')}
                  className="mt-0.5 text-purple-600 focus:ring-purple-500"
                />
                <div>
                  <span className="font-medium text-gray-900">A career path I want to pursue</span>
                  <p className="text-sm text-gray-500">Enter a role like "Software Engineer" or "Product Manager"</p>
                </div>
              </label>
            </div>

            {/* Conditional input */}
            {goalType === 'job_posting' && (
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Job Description</label>
                <textarea
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  rows={6}
                  placeholder="Paste the full job description here..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                />
              </div>
            )}

            {goalType === 'career_path' && (
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Career Path / Role</label>
                <input
                  type="text"
                  value={careerPath}
                  onChange={(e) => setCareerPath(e.target.value)}
                  placeholder="e.g. Software Engineer, Product Manager, Data Analyst..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>
            )}
          </div>

          {/* Step 2: Experience Level */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">2. Experience Level</h2>
            <select
              value={experienceLevel}
              onChange={(e) => setExperienceLevel(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              {experienceLevels.map((level) => (
                <option key={level.value} value={level.value}>
                  {level.label}
                </option>
              ))}
            </select>
          </div>

          {/* Step 3: Interview Type */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">3. Interview Type</h2>
            <div className="grid grid-cols-3 gap-3">
              {interviewTypes.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => setInterviewType(type.value)}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${
                    interviewType === type.value
                      ? 'border-purple-500 bg-purple-50'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  <div className="text-2xl mb-2">{type.icon}</div>
                  <div className="font-medium text-gray-900 text-sm">{type.label}</div>
                  <div className="text-xs text-gray-500 mt-1">{type.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Step 4: Mode */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">4. Interview Mode</h2>
            <div className="grid grid-cols-2 gap-3">
              {modes.map((m) => (
                <button
                  key={m.value}
                  type="button"
                  onClick={() => setMode(m.value)}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${
                    mode === m.value
                      ? 'border-purple-500 bg-purple-50'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  <div className="text-2xl mb-2">{m.icon}</div>
                  <div className="font-medium text-gray-900 text-sm">{m.label}</div>
                  <div className="text-xs text-gray-500 mt-1">{m.description}</div>
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-purple-600 text-white py-4 rounded-xl font-semibold text-base hover:bg-purple-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-3"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                Generating your interview questions...
              </>
            ) : (
              'Start Interview →'
            )}
          </button>
        </form>
      </main>
    </div>
  )
}
