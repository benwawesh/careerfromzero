'use client'

import { useState } from 'react'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import TokenBalance from '@/components/TokenBalance'
import { apiFetch } from '@/lib/apiFetch'

export default function CVWriterPage() {
  return (
    <ProtectedRoute>
      <CVWriter />
    </ProtectedRoute>
  )
}

function CVWriter() {
  const [activeTab, setActiveTab] = useState<'write' | 'revamp'>('write')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState('')
  const [error, setError] = useState('')

  // Write from scratch form
  const [writeForm, setWriteForm] = useState({
    full_name: '', email: '', phone: '', location: '',
    job_title: '', years_experience: '', skills: '',
    summary: '', work_experience: '', education: '',
    linkedin_url: '',
  })

  // Revamp form
  const [revampForm, setRevampForm] = useState({
    cv_text: '',
    target_job: '',
  })

  const handleWrite = async () => {
    const required = ['full_name', 'email', 'job_title', 'skills']
    const missing = required.filter(f => !writeForm[f as keyof typeof writeForm])
    if (missing.length) {
      setError(`Please fill in: ${missing.join(', ')}`)
      return
    }
    setLoading(true)
    setError('')
    setResult('')
    try {
      const res = await apiFetch('/api/ai/cv/write/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(writeForm),
      })
      const data = await res.json()
      if (res.ok && data.success) {
        setResult(data.cv_text)
      } else if (res.status === 402) {
        setError(data.message || 'Insufficient credits. Please top up.')
      } else {
        setError(data.message || 'CV generation failed. Please try again.')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleRevamp = async () => {
    if (!revampForm.cv_text.trim()) {
      setError('Please paste your existing CV text.')
      return
    }
    setLoading(true)
    setError('')
    setResult('')
    try {
      const res = await apiFetch('/api/ai/cv/revamp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(revampForm),
      })
      const data = await res.json()
      if (res.ok && data.success) {
        setResult(data.cv_text)
      } else if (res.status === 402) {
        setError(data.message || 'Insufficient credits. Please top up.')
      } else {
        setError(data.message || 'CV revamp failed. Please try again.')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(result)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <Link href="/dashboard" className="text-gray-500 hover:text-gray-900 text-sm">← Dashboard</Link>
            <h1 className="text-2xl font-bold text-gray-900 mt-1">AI CV Writer</h1>
            <p className="text-gray-500 text-sm">Write or revamp your CV with AI</p>
          </div>
          <TokenBalance />
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-6">
        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-sm p-2 inline-flex gap-2 mb-6">
          <button
            onClick={() => { setActiveTab('write'); setResult(''); setError('') }}
            className={`px-6 py-2.5 rounded-lg font-medium transition-colors ${
              activeTab === 'write' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Write from Scratch
            <span className="ml-2 text-xs opacity-75">50 credits</span>
          </button>
          <button
            onClick={() => { setActiveTab('revamp'); setResult(''); setError('') }}
            className={`px-6 py-2.5 rounded-lg font-medium transition-colors ${
              activeTab === 'revamp' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Revamp Existing CV
            <span className="ml-2 text-xs opacity-75">30 credits</span>
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
          <div className="bg-white rounded-lg shadow-sm p-6">
            {activeTab === 'write' ? (
              <>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Your Information</h2>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
                      <input type="text" value={writeForm.full_name}
                        onChange={e => setWriteForm({ ...writeForm, full_name: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        placeholder="John Doe" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                      <input type="email" value={writeForm.email}
                        onChange={e => setWriteForm({ ...writeForm, email: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        placeholder="john@example.com" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                      <input type="tel" value={writeForm.phone}
                        onChange={e => setWriteForm({ ...writeForm, phone: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        placeholder="+254 712 345 678" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
                      <input type="text" value={writeForm.location}
                        onChange={e => setWriteForm({ ...writeForm, location: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        placeholder="Nairobi, Kenya" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Target Job Title *</label>
                      <input type="text" value={writeForm.job_title}
                        onChange={e => setWriteForm({ ...writeForm, job_title: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        placeholder="Software Engineer" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Years of Experience</label>
                      <input type="number" value={writeForm.years_experience}
                        onChange={e => setWriteForm({ ...writeForm, years_experience: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        placeholder="5" min="0" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Skills * <span className="text-gray-400 font-normal">(comma separated)</span></label>
                    <textarea value={writeForm.skills}
                      onChange={e => setWriteForm({ ...writeForm, skills: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                      rows={2} placeholder="Python, Django, React, SQL, Docker" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Professional Summary</label>
                    <textarea value={writeForm.summary}
                      onChange={e => setWriteForm({ ...writeForm, summary: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                      rows={3} placeholder="Brief overview of your professional background..." />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Work Experience</label>
                    <textarea value={writeForm.work_experience}
                      onChange={e => setWriteForm({ ...writeForm, work_experience: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                      rows={4} placeholder="Company - Role (2021-Present): What you did..." />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Education</label>
                    <textarea value={writeForm.education}
                      onChange={e => setWriteForm({ ...writeForm, education: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                      rows={2} placeholder="BSc Computer Science, University of Nairobi (2018)" />
                  </div>
                  <button onClick={handleWrite} disabled={loading}
                    className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2">
                    {loading ? (
                      <><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" /> Generating CV...</>
                    ) : 'Generate CV — 50 credits'}
                  </button>
                </div>
              </>
            ) : (
              <>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Your Existing CV</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Target Job Role <span className="text-gray-400 font-normal">(optional)</span></label>
                    <input type="text" value={revampForm.target_job}
                      onChange={e => setRevampForm({ ...revampForm, target_job: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                      placeholder="e.g. Senior Software Engineer" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Paste Your CV Text *</label>
                    <textarea value={revampForm.cv_text}
                      onChange={e => setRevampForm({ ...revampForm, cv_text: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                      rows={16} placeholder="Paste your existing CV text here..." />
                  </div>
                  <button onClick={handleRevamp} disabled={loading}
                    className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2">
                    {loading ? (
                      <><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" /> Revamping CV...</>
                    ) : 'Revamp CV — 30 credits'}
                  </button>
                </div>
              </>
            )}
          </div>

          {/* Output Panel */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Generated CV</h2>
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
                <p className="text-sm">AI is writing your CV...</p>
                <p className="text-xs mt-1">This takes 15-30 seconds</p>
              </div>
            ) : result ? (
              <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-gray-50 p-4 rounded-lg overflow-auto max-h-[600px] leading-relaxed">
                {result}
              </pre>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <svg className="w-16 h-16 mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-sm">Your AI-generated CV will appear here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
