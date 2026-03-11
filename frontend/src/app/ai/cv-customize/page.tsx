'use client'

import { useState } from 'react'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import TokenBalance from '@/components/TokenBalance'
import { apiFetch } from '@/lib/apiFetch'

export default function CVCustomizePage() {
  return (
    <ProtectedRoute>
      <CVCustomize />
    </ProtectedRoute>
  )
}

function CVCustomize() {
  const [activeTab, setActiveTab] = useState<'customize' | 'cover-letter'>('customize')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState('')
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    cv_text: '',
    job_description: '',
    job_title: '',
    company_name: '',
    applicant_name: '',
  })

  const handleSubmit = async () => {
    if (!form.cv_text.trim() || !form.job_description.trim()) {
      setError('Please provide both your CV and the job description.')
      return
    }
    setLoading(true)
    setError('')
    setResult('')

    const endpoint = activeTab === 'customize' ? '/api/ai/cv/customize/' : '/api/ai/cv/cover-letter/'

    try {
      const res = await apiFetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (res.ok && data.success) {
        setResult(activeTab === 'customize' ? data.cv_text : data.cover_letter)
      } else if (res.status === 402) {
        setError(data.message || 'Insufficient credits. Please top up.')
      } else {
        setError(data.message || 'Generation failed. Please try again.')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = () => navigator.clipboard.writeText(result)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <Link href="/dashboard" className="text-gray-500 hover:text-gray-900 text-sm">← Dashboard</Link>
            <h1 className="text-2xl font-bold text-gray-900 mt-1">CV Customization</h1>
            <p className="text-gray-500 text-sm">Tailor your CV or write a cover letter for a specific job</p>
          </div>
          <TokenBalance />
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-6">
        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-sm p-2 inline-flex gap-2 mb-6">
          <button
            onClick={() => { setActiveTab('customize'); setResult(''); setError('') }}
            className={`px-6 py-2.5 rounded-lg font-medium transition-colors ${
              activeTab === 'customize' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Customize CV for Job
            <span className="ml-2 text-xs opacity-75">20 credits</span>
          </button>
          <button
            onClick={() => { setActiveTab('cover-letter'); setResult(''); setError('') }}
            className={`px-6 py-2.5 rounded-lg font-medium transition-colors ${
              activeTab === 'cover-letter' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Write Cover Letter
            <span className="ml-2 text-xs opacity-75">20 credits</span>
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center justify-between">
            <span>{error}</span>
            {error.includes('credits') && (
              <Link href="/payments" className="ml-4 bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700">
                Top Up
              </Link>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Input Panel */}
          <div className="bg-white rounded-lg shadow-sm p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">
              {activeTab === 'customize' ? 'Job Details' : 'Job & Applicant Details'}
            </h2>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Job Title</label>
                <input type="text" value={form.job_title}
                  onChange={e => setForm({ ...form, job_title: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  placeholder="e.g. Software Engineer" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Company Name</label>
                <input type="text" value={form.company_name}
                  onChange={e => setForm({ ...form, company_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  placeholder="e.g. Safaricom" />
              </div>
            </div>

            {activeTab === 'cover-letter' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Your Name</label>
                <input type="text" value={form.applicant_name}
                  onChange={e => setForm({ ...form, applicant_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  placeholder="Your full name" />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Job Description *</label>
              <textarea value={form.job_description}
                onChange={e => setForm({ ...form, job_description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                rows={7} placeholder="Paste the full job description here..." />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Your CV Text *</label>
              <textarea value={form.cv_text}
                onChange={e => setForm({ ...form, cv_text: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                rows={7} placeholder="Paste your CV text here..." />
            </div>

            <button onClick={handleSubmit} disabled={loading}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2">
              {loading ? (
                <><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                  {activeTab === 'customize' ? 'Customizing CV...' : 'Writing Cover Letter...'}</>
              ) : activeTab === 'customize' ? 'Customize CV — 20 credits' : 'Write Cover Letter — 20 credits'}
            </button>
          </div>

          {/* Output Panel */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">
                {activeTab === 'customize' ? 'Customized CV' : 'Cover Letter'}
              </h2>
              {result && (
                <button onClick={copyToClipboard}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 border border-blue-200 px-3 py-1 rounded-lg hover:bg-blue-50">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                  </svg>
                  Copy
                </button>
              )}
            </div>
            {loading ? (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-4" />
                <p className="text-sm">AI is working on it...</p>
                <p className="text-xs mt-1">This takes 15-30 seconds</p>
              </div>
            ) : result ? (
              <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-gray-50 p-4 rounded-lg overflow-auto max-h-[600px] leading-relaxed">
                {result}
              </pre>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <svg className="w-16 h-16 mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
                    d={activeTab === 'customize'
                      ? "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      : "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    } />
                </svg>
                <p className="text-sm">
                  {activeTab === 'customize' ? 'Your tailored CV will appear here' : 'Your cover letter will appear here'}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
