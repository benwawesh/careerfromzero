'use client'

import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'

export default function Home() {
  const { isAuthenticated, isAdmin } = useAuth()

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Career AI
              </span>
            </div>
            {isAuthenticated ? (
              <div className="flex space-x-4">
                {isAdmin && (
                  <Link 
                    href="/admin/dashboard"
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    Admin Dashboard
                  </Link>
                )}
                <Link 
                  href="/dashboard"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Dashboard
                </Link>
              </div>
            ) : (
              <div className="flex space-x-4">
                <Link 
                  href="/login"
                  className="px-4 py-2 text-gray-600 hover:text-blue-600 transition-colors"
                >
                  Login
                </Link>
                <Link 
                  href="/register"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              AI-Powered Career Operating System
            </span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Transform your job search with intelligent AI agents that help you build CVs, 
            discover jobs, practice interviews, and simulate real work experiences.
          </p>
          <div className="flex justify-center space-x-4">
            <Link 
              href="/register"
              className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-semibold hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg hover:shadow-xl"
            >
              Start Free Trial
            </Link>
            <Link 
              href="/dashboard"
              className="px-8 py-3 bg-white text-gray-700 border-2 border-gray-300 rounded-lg font-semibold hover:border-blue-600 hover:text-blue-600 transition-all"
            >
              View Dashboard
            </Link>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
          Six Powerful AI Agents
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {/* CV Builder */}
          <div className="bg-white p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl">📄</span>
            </div>
            <h3 className="text-xl font-semibold mb-2">CV Builder & Optimizer</h3>
            <p className="text-gray-600">
              Create, optimize, and customize CVs for specific jobs. Upload existing CVs or build from scratch with AI assistance.
            </p>
          </div>

          {/* Job Discovery */}
          <div className="bg-white p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl">🔍</span>
            </div>
            <h3 className="text-xl font-semibold mb-2">Job Discovery Agent</h3>
            <p className="text-gray-600">
              Search multiple job boards and APIs to find opportunities matching your preferences, location, and salary expectations.
            </p>
          </div>

          {/* Job Application */}
          <div className="bg-white p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl">🚀</span>
            </div>
            <h3 className="text-xl font-semibold mb-2">Job Application Agent</h3>
            <p className="text-gray-600">
              Automate job applications with personalized cover letters and CVs tailored to each job posting.
            </p>
          </div>

          {/* Interview Simulation */}
          <div className="bg-white p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl">🎤</span>
            </div>
            <h3 className="text-xl font-semibold mb-2">Interview Simulation</h3>
            <p className="text-gray-600">
              Practice with interactive AI mock interviews. Receive real-time feedback on communication, confidence, and answers.
            </p>
          </div>

          {/* Job Simulation */}
          <div className="bg-white p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl">💼</span>
            </div>
            <h3 className="text-xl font-semibold mb-2">Job Simulation Agent</h3>
            <p className="text-gray-600">
              Experience realistic work tasks - handle customer support, solve coding problems, or perform role-based job scenarios.
            </p>
          </div>

          {/* Career Guidance */}
          <div className="bg-white p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl">🎯</span>
            </div>
            <h3 className="text-xl font-semibold mb-2">Career Guidance Agent</h3>
            <p className="text-gray-600">
              Get personalized career recommendations, identify skill gaps, and receive learning paths based on your profile.
            </p>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="bg-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            How It Works
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-600 text-white rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold">
                1
              </div>
              <h3 className="text-xl font-semibold mb-2">Create Your Profile</h3>
              <p className="text-gray-600">
                Sign up and build your professional profile with your skills, experience, and career goals.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-600 text-white rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold">
                2
              </div>
              <h3 className="text-xl font-semibold mb-2">Let AI Assist You</h3>
              <p className="text-gray-600">
                Use AI agents to build your CV, discover jobs, practice interviews, and simulate work experiences.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-green-600 text-white rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold">
                3
              </div>
              <h3 className="text-xl font-semibold mb-2">Land Your Dream Job</h3>
              <p className="text-gray-600">
                Apply with confidence, get AI-powered feedback, and track your progress to success.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-12 text-center text-white">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Ready to Transform Your Career?
          </h2>
          <p className="text-lg mb-8 text-blue-100">
            Join thousands of professionals using AI to accelerate their career growth.
          </p>
          <Link 
            href="/register"
            className="px-8 py-3 bg-white text-blue-600 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
          >
            Get Started Free
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-lg font-semibold mb-4">Career AI</h3>
              <p className="text-gray-400">
                AI-driven Career Operating System helping you find your dream job.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Features</h4>
              <ul className="space-y-2 text-gray-400">
                <li><Link href="#" className="hover:text-white">CV Builder</Link></li>
                <li><Link href="#" className="hover:text-white">Job Search</Link></li>
                <li><Link href="#" className="hover:text-white">Interview Practice</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-gray-400">
                <li><Link href="#" className="hover:text-white">About</Link></li>
                <li><Link href="#" className="hover:text-white">Blog</Link></li>
                <li><Link href="#" className="hover:text-white">Contact</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-gray-400">
                <li><Link href="#" className="hover:text-white">Privacy</Link></li>
                <li><Link href="#" className="hover:text-white">Terms</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2026 Career AI System. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </main>
  )
}