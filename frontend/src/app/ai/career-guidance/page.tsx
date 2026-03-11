'use client'

import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import TokenBalance from '@/components/TokenBalance'
import { apiFetch } from '@/lib/apiFetch'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function CareerGuidancePage() {
  return (
    <ProtectedRoute>
      <CareerGuidance />
    </ProtectedRoute>
  )
}

function CareerGuidance() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "Hello! I'm your AI career advisor. I can help you with career path planning, job search strategies, skill development, salary negotiation, and more. What would you like to discuss today?",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [balance, setBalance] = useState<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    apiFetch('/api/payments/balance/').then(r => r.ok ? r.json() : null).then(d => {
      if (d) setBalance(d.balance)
    })
  }, [])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return

    setInput('')
    setError('')
    const newMessages: Message[] = [...messages, { role: 'user', content: text }]
    setMessages(newMessages)
    setLoading(true)

    const res = await apiFetch('/api/ai/career/guidance/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        history: newMessages.slice(-10),
      }),
    })

    const data = await res.json()
    setLoading(false)

    if (res.ok && data.success) {
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
      if (balance !== null) setBalance(b => b !== null ? Math.max(0, b - 10) : null)
    } else if (res.status === 402) {
      setError(data.message)
    } else {
      setError(data.message || 'Something went wrong. Please try again.')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow flex-shrink-0">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <Link href="/dashboard" className="text-gray-500 hover:text-gray-900 text-sm">← Dashboard</Link>
            <h1 className="text-xl font-bold text-gray-900 mt-1">Career Guidance</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500">10 credits/message</span>
            <TokenBalance />
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto max-w-4xl w-full mx-auto px-4 py-6 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-2xl px-4 py-3 rounded-2xl text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-br-sm'
                : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'0ms'}} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'150ms'}} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'300ms'}} />
              </div>
            </div>
          </div>
        )}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
            <span>{error}</span>
            {error.includes('credits') && (
              <Link href="/payments" className="ml-4 bg-red-600 text-white px-3 py-1 rounded-lg text-xs font-semibold hover:bg-red-700 flex-shrink-0">
                Top Up
              </Link>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex-shrink-0 bg-white border-t border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder="Ask for career advice..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="bg-blue-600 text-white px-5 py-3 rounded-xl font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2 text-center">Each message costs 10 credits</p>
        </div>
      </div>
    </div>
  )
}
