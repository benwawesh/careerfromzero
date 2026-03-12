'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

type UUID = string

interface CV {
  id: UUID
  title: string
  original_filename: string
  file_type: string
  file_size: number
  has_data: boolean
  has_analysis: boolean
  versions_count: number
  uploaded_at: string
}

export default function CVListPage() {
  return (
    <ProtectedRoute>
      <CVList />
    </ProtectedRoute>
  )
}

function CVList() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [cvs, setCvs] = useState<CV[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadTitle, setUploadTitle] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [showUpload, setShowUpload] = useState(false)
  const [error, setError] = useState('')
  const [dragOver, setDragOver] = useState(false)

  useEffect(() => {
    fetchCVs()
  }, [])

  const fetchCVs = async () => {
    setLoading(true)
    try {
      const res = await apiFetch('/api/cv/')
      if (res.ok) {
        const data = await res.json()
        setCvs(data.results || data)
      }
    } catch {
      setError('Failed to load CVs')
    } finally {
      setLoading(false)
    }
  }

  const handleFileSelect = (file: File) => {
    setSelectedFile(file)
    if (!uploadTitle) setUploadTitle(file.name.replace(/\.[^/.]+$/, ''))
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileSelect(file)
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile || !uploadTitle) return

    setUploading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('title', uploadTitle)

      const res = await apiFetch('/api/cv/upload/', {
        method: 'POST',
        body: formData,
      })

      if (res.ok) {
        const data = await res.json()
        setShowUpload(false)
        setSelectedFile(null)
        setUploadTitle('')
        router.push(`/cv/${data.id}`)
      } else {
        const data = await res.json()
        setError(data.error || data.file?.[0] || 'Upload failed')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id: UUID) => {
    if (!confirm('Delete this CV?')) return
    const res = await apiFetch(`/api/cv/${id}/`, { method: 'DELETE' })
    if (res.ok) fetchCVs()
  }

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">My CVs</h1>
            <p className="text-sm text-gray-500">{cvs.length} CV{cvs.length !== 1 ? 's' : ''} saved</p>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="text-gray-600 hover:text-gray-900 text-sm">Dashboard</Link>
            <button
              onClick={() => setShowUpload(true)}
              className="border border-blue-600 text-blue-600 px-4 py-2 rounded-lg hover:bg-blue-50 text-sm font-medium"
            >
              Upload CV
            </button>
            <Link
              href="/cv/builder"
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 text-sm font-medium"
            >
              ✨ Build with AI
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Upload Modal */}
        {showUpload && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
              <div className="p-6">
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-bold text-gray-900">Upload CV</h2>
                  <button onClick={() => { setShowUpload(false); setSelectedFile(null); setUploadTitle('') }}
                    className="text-gray-400 hover:text-gray-600 text-2xl leading-none">
                    &times;
                  </button>
                </div>

                <form onSubmit={handleUpload} className="space-y-4">
                  {/* Drop zone */}
                  <div
                    onDrop={handleDrop}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                    onDragLeave={() => setDragOver(false)}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                      dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.docx"
                      className="hidden"
                      onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                    />
                    {selectedFile ? (
                      <div>
                        <p className="font-medium text-gray-900">{selectedFile.name}</p>
                        <p className="text-sm text-gray-500 mt-1">{formatBytes(selectedFile.size)}</p>
                      </div>
                    ) : (
                      <div>
                        <p className="text-gray-600">Drop your CV here or click to browse</p>
                        <p className="text-sm text-gray-400 mt-1">PDF or DOCX, max 10MB</p>
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">CV Title</label>
                    <input
                      type="text"
                      value={uploadTitle}
                      onChange={(e) => setUploadTitle(e.target.value)}
                      required
                      placeholder="e.g. Software Engineer CV"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  {error && <p className="text-red-600 text-sm">{error}</p>}

                  <button
                    type="submit"
                    disabled={uploading || !selectedFile}
                    className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {uploading ? 'Uploading & Parsing...' : 'Upload CV'}
                  </button>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* CV Grid */}
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : cvs.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">📄</span>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No CVs yet</h3>
            <p className="text-gray-500 mb-6">Upload your CV to get started with AI-powered optimization</p>
            <button
              onClick={() => setShowUpload(true)}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
            >
              Upload Your First CV
            </button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cvs.map((cv) => (
              <div key={cv.id} className="bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-100">
                <div className="p-6">
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <span className="text-lg">{cv.file_type === 'PDF' ? '📄' : '📝'}</span>
                    </div>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded font-medium">
                      {cv.file_type}
                    </span>
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-1 truncate">{cv.title}</h3>
                  <p className="text-xs text-gray-400 mb-4">{formatBytes(cv.file_size)}</p>

                  <div className="flex gap-2 mb-4">
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                      cv.has_data ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                    }`}>
                      {cv.has_data ? 'Parsed' : 'Not parsed'}
                    </span>
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                      cv.has_analysis ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-500'
                    }`}>
                      {cv.has_analysis ? 'Analyzed' : 'Not analyzed'}
                    </span>
                  </div>

                  <div className="flex gap-2">
                    <Link
                      href={`/cv/${cv.id}`}
                      className="flex-1 bg-blue-600 text-white text-sm text-center py-2 rounded-lg hover:bg-blue-700"
                    >
                      View
                    </Link>
                    <button
                      onClick={() => handleDelete(cv.id)}
                      className="px-3 py-2 border border-red-200 text-red-500 rounded-lg hover:bg-red-50 text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
