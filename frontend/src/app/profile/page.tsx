'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import ProtectedRoute from '@/components/ProtectedRoute'
import Link from 'next/link'

interface ProfileForm {
  first_name: string
  last_name: string
  phone_number: string
  bio: string
  location: string
  linkedin_url: string
  github_url: string
  portfolio_url: string
  career_goals: string
}

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <Profile />
    </ProtectedRoute>
  )
}

function Profile() {
  const { user, logout } = useAuth()
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const [form, setForm] = useState<ProfileForm>({
    first_name: '',
    last_name: '',
    phone_number: '',
    bio: '',
    location: '',
    linkedin_url: '',
    github_url: '',
    portfolio_url: '',
    career_goals: '',
  })

  useEffect(() => {
    if (user) {
      setForm({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        phone_number: '',
        bio: '',
        location: '',
        linkedin_url: '',
        github_url: '',
        portfolio_url: '',
        career_goals: '',
      })
      // Fetch full profile to get optional fields
      fetchProfile()
    }
  }, [user])

  const fetchProfile = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/profile/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.ok) {
        const data = await response.json()
        setForm({
          first_name: data.first_name || '',
          last_name: data.last_name || '',
          phone_number: data.phone_number || '',
          bio: data.bio || '',
          location: data.location || '',
          linkedin_url: data.linkedin_url || '',
          github_url: data.github_url || '',
          portfolio_url: data.portfolio_url || '',
          career_goals: data.career_goals || '',
        })
      }
    } catch {
      // silently fail — form will show data from auth context
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/profile/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(form),
      })
      if (response.ok) {
        setSuccess('Profile updated successfully')
        setEditing(false)
      } else {
        const data = await response.json()
        setError(data.error || 'Failed to update profile')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const field = (label: string, key: keyof ProfileForm, type = 'text', placeholder = '') => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {editing ? (
        type === 'textarea' ? (
          <textarea
            value={form[key]}
            onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            rows={3}
            placeholder={placeholder}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        ) : (
          <input
            type={type}
            value={form[key]}
            onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            placeholder={placeholder}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        )
      ) : (
        <p className="text-gray-900 py-2">
          {form[key] || <span className="text-gray-400 italic">Not set</span>}
        </p>
      )}
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">My Profile</h1>
            <p className="text-sm text-gray-500">@{user?.username}</p>
          </div>
          <div className="flex items-center space-x-4">
            <Link href="/dashboard" className="text-gray-600 hover:text-gray-900">
              Dashboard
            </Link>
            <button
              onClick={logout}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {success && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-6">
            {success}
          </div>
        )}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          {/* Profile header */}
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-8">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-20 h-20 rounded-full bg-white bg-opacity-20 flex items-center justify-center text-white text-3xl font-bold">
                  {user?.first_name?.[0]}{user?.last_name?.[0]}
                </div>
                <div className="text-white">
                  <h2 className="text-2xl font-bold">{user?.first_name} {user?.last_name}</h2>
                  <p className="text-blue-100">{user?.email}</p>
                </div>
              </div>
              <button
                onClick={() => editing ? handleSave() : setEditing(true)}
                disabled={saving}
                className="bg-white text-blue-600 px-4 py-2 rounded-lg font-medium hover:bg-blue-50 disabled:opacity-50"
              >
                {saving ? 'Saving...' : editing ? 'Save Changes' : 'Edit Profile'}
              </button>
            </div>
          </div>

          <div className="p-8 space-y-8">
            {/* Basic info */}
            <section>
              <h3 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
                Basic Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {field('First Name', 'first_name')}
                {field('Last Name', 'last_name')}
                {field('Phone Number', 'phone_number', 'tel', '+1 (555) 000-0000')}
                {field('Location', 'location', 'text', 'City, Country')}
              </div>
            </section>

            {/* About */}
            <section>
              <h3 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">About</h3>
              <div className="space-y-4">
                {field('Bio', 'bio', 'textarea', 'Tell us about yourself...')}
                {field('Career Goals', 'career_goals', 'textarea', 'What are you looking to achieve in your career?')}
              </div>
            </section>

            {/* Links */}
            <section>
              <h3 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
                Professional Links
              </h3>
              <div className="space-y-4">
                {field('LinkedIn URL', 'linkedin_url', 'url', 'https://linkedin.com/in/yourprofile')}
                {field('GitHub URL', 'github_url', 'url', 'https://github.com/yourusername')}
                {field('Portfolio URL', 'portfolio_url', 'url', 'https://yourportfolio.com')}
              </div>
            </section>

            {editing && (
              <div className="flex space-x-4 pt-4">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
                <button
                  onClick={() => { setEditing(false); setError('') }}
                  className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
