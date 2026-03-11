'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

function PaymentSuccessContent() {
  const searchParams = useSearchParams()
  const paymentId = searchParams.get('payment_id')
  const [credits, setCredits] = useState<number | null>(null)
  const [balance, setBalance] = useState<number | null>(null)

  useEffect(() => {
    const load = async () => {
      if (paymentId) {
        const res = await apiFetch(`/api/payments/status/${paymentId}/`)
        if (res.ok) {
          const data = await res.json()
          setCredits(data.credits)
        }
      }
      const balRes = await apiFetch('/api/payments/balance/')
      if (balRes.ok) {
        const data = await balRes.json()
        setBalance(data.balance)
      }
    }
    load()
  }, [paymentId])

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-lg p-10 max-w-md w-full text-center">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <svg className="w-10 h-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Payment Successful!</h1>
        {credits !== null && (
          <p className="text-gray-600 mb-2">
            <span className="font-semibold text-blue-600 text-xl">{credits} credits</span> have been added to your account.
          </p>
        )}
        {balance !== null && (
          <p className="text-gray-500 text-sm mb-6">Your new balance: <strong>{balance} credits</strong></p>
        )}
        <div className="flex flex-col gap-3">
          <Link href="/cv" className="bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700">
            Write or Revamp Your CV
          </Link>
          <Link href="/dashboard" className="border border-gray-300 text-gray-700 py-3 rounded-lg font-semibold hover:bg-gray-50">
            Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}

export default function PaymentSuccessPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    }>
      <PaymentSuccessContent />
    </Suspense>
  )
}
