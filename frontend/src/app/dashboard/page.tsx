'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import Link from 'next/link'
import TokenBalance from '@/components/TokenBalance'

export default function Dashboard() {
  const { user, isAuthenticated, loading, logout } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, loading, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated || !user) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Career AI System</h1>
              <p className="text-sm text-gray-600">Welcome back, {user.first_name}!</p>
            </div>
            <div className="flex items-center space-x-4">
              <TokenBalance />
              <Link href="/activity" className="text-gray-600 hover:text-gray-900 text-sm font-medium">
                My Activity
              </Link>
              <Link href="/profile" className="text-gray-600 hover:text-gray-900">
                Profile
              </Link>
              <button
                onClick={logout}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            Welcome to Your Career AI Assistant
          </h2>
          <p className="text-gray-600">
            Build your professional profile, discover jobs, and prepare for interviews with AI-powered tools.
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {/* AI Curation Card */}
          <div className="bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow text-white">
            <div className="flex items-center mb-4">
              <div className="bg-white/20 p-3 rounded-full">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold ml-3">AI Job Curation</h3>
            </div>
            <p className="text-blue-50 mb-4">
              Let AI curate the perfect jobs for you. Choose an existing CV or enter your details to get personalized job matches.
            </p>
            <Link href="/jobs/ai-curate" className="block w-full bg-white text-blue-600 py-2 rounded-lg hover:bg-blue-50 transition-colors text-center font-semibold">
              Start AI Curation
            </Link>
          </div>

          {/* CV Builder Card */}
          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-center mb-4">
              <div className="bg-blue-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 ml-3">CV Builder</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Create, optimize, and customize your CV with AI assistance for ATS systems.
            </p>
            <Link href="/cv" className="block w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors text-center">
              Build Your CV
            </Link>
          </div>

          {/* Job Discovery Card */}
          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-center mb-4">
              <div className="bg-green-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 ml-3">Job Discovery</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Find job opportunities from multiple boards tailored to your preferences.
            </p>
            <Link href="/jobs" className="block w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition-colors text-center">
              Search Jobs
            </Link>
          </div>

          {/* Interview Practice Card */}
          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-center mb-4">
              <div className="bg-purple-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 ml-3">Interview Practice</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Practice with Alex, your AI interview coach. Get scored feedback and a final report.
            </p>
            <Link href="/interview" className="block w-full bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-700 transition-colors text-center">
              Start Interview
            </Link>
          </div>

          {/* Job Simulation Card */}
          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-center mb-4">
              <div className="bg-orange-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 ml-3">Job Simulation</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Experience realistic work scenarios to build job-ready skills.
            </p>
            <button className="w-full bg-orange-600 text-white py-2 rounded-lg hover:bg-orange-700 transition-colors">
              Start Simulation
            </button>
          </div>

          {/* Career Guidance Card */}
          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-center mb-4">
              <div className="bg-pink-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-pink-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 ml-3">Career Guidance</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Get AI-powered career advice and skill gap analysis.
            </p>
            <Link href="/ai/career-guidance" className="block w-full bg-pink-600 text-white py-2 rounded-lg hover:bg-pink-700 transition-colors text-center">
              Get Guidance
            </Link>
          </div>

          {/* AI CV Writer Card */}
          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-center mb-4">
              <div className="bg-blue-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 ml-3">AI CV Writer</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Write a professional CV from scratch or revamp your existing one with AI.
            </p>
            <Link href="/ai/cv-writer" className="block w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors text-center">
              Write CV
            </Link>
          </div>

          {/* CV Customization Card */}
          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-center mb-4">
              <div className="bg-teal-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 ml-3">CV Customization</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Tailor your CV for a specific job or generate a cover letter automatically.
            </p>
            <Link href="/ai/cv-customize" className="block w-full bg-teal-600 text-white py-2 rounded-lg hover:bg-teal-700 transition-colors text-center">
              Customize CV
            </Link>
          </div>

          {/* Applications Card */}
          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-center mb-4">
              <div className="bg-indigo-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 ml-3">My Applications</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Track and manage your job applications in one place.
            </p>
            <button className="w-full bg-indigo-600 text-white py-2 rounded-lg hover:bg-indigo-700 transition-colors">
              View Applications
            </button>
          </div>
        </div>

        {/* Activity CTA */}
        <div className="bg-white rounded-lg shadow-md p-6 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Track your progress</h3>
            <p className="text-gray-500 text-sm mt-1">View your interview history, coaching sessions, scores, and topics completed.</p>
          </div>
          <Link href="/activity" className="bg-gray-900 text-white px-5 py-2.5 rounded-lg hover:bg-gray-700 text-sm font-medium shrink-0 ml-6">
            My Activity →
          </Link>
        </div>
      </main>
    </div>
  )
}