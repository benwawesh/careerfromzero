'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

export default function TokenBalance() {
  const [balance, setBalance] = useState<number | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiFetch('/api/payments/balance/')
        if (res.ok) {
          const data = await res.json()
          setBalance(data.balance)
        }
      } catch {}
    }
    load()
    // Refresh every 60 seconds
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [])

  if (balance === null) return null

  return (
    <Link
      href="/payments"
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors ${
        balance === 0
          ? 'bg-red-50 border-red-200 text-red-700 hover:bg-red-100'
          : balance < 20
          ? 'bg-yellow-50 border-yellow-200 text-yellow-700 hover:bg-yellow-100'
          : 'bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100'
      }`}
    >
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <span>{balance} credits</span>
      {balance === 0 && <span className="text-xs">— Top up</span>}
    </Link>
  )
}
