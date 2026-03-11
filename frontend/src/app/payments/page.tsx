'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

interface TokenPack {
  id: number
  name: string
  description: string
  credits: number
  price_kes: number
  is_featured: boolean
}

interface TokenBalance {
  balance: number
  total_purchased: number
  total_used: number
  recent_transactions: {
    type: string
    credits: number
    balance_after: number
    description: string
    date: string
  }[]
}

export default function PaymentsPage() {
  return (
    <ProtectedRoute>
      <Payments />
    </ProtectedRoute>
  )
}

function Payments() {
  const router = useRouter()
  const [packs, setPacks] = useState<TokenPack[]>([])
  const [balance, setBalance] = useState<TokenBalance | null>(null)
  const [selectedPack, setSelectedPack] = useState<TokenPack | null>(null)
  const [paymentMethod, setPaymentMethod] = useState<'mpesa' | 'card'>('mpesa')
  const [phone, setPhone] = useState('')
  const [loading, setLoading] = useState(true)
  const [paying, setPaying] = useState(false)
  const [error, setError] = useState('')
  const [pendingPaymentId, setPendingPaymentId] = useState('')
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null)
  const [paymentStatus, setPaymentStatus] = useState('')

  useEffect(() => {
    loadData()
    return () => { if (pollInterval) clearInterval(pollInterval) }
  }, [])

  const loadData = async () => {
    setLoading(true)
    const [packsRes, balanceRes] = await Promise.all([
      apiFetch('/api/payments/packs/'),
      apiFetch('/api/payments/balance/'),
    ])
    if (packsRes.ok) setPacks(await packsRes.json())
    if (balanceRes.ok) setBalance(await balanceRes.json())
    setLoading(false)
  }

  const handleMpesaPay = async () => {
    if (!selectedPack) return setError('Select a token pack first')
    if (!phone.trim()) return setError('Enter your M-Pesa phone number')

    setPaying(true)
    setError('')
    setPaymentStatus('Sending payment request to your phone...')

    const res = await apiFetch('/api/payments/mpesa/initiate/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pack_id: selectedPack.id, phone: phone.trim() }),
    })

    const data = await res.json()

    if (res.ok && data.success) {
      setPendingPaymentId(data.payment_id)
      setPaymentStatus('Check your phone and enter your M-Pesa PIN...')
      startPolling(data.payment_id)
    } else {
      setError(data.message || 'Payment initiation failed')
      setPaymentStatus('')
      setPaying(false)
    }
  }

  const handleCardPay = async () => {
    if (!selectedPack) return setError('Select a token pack first')

    setPaying(true)
    setError('')

    const res = await apiFetch('/api/payments/card/initiate/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pack_id: selectedPack.id }),
    })

    const data = await res.json()

    if (res.ok && data.success) {
      // Redirect to Flutterwave payment page
      window.location.href = data.payment_link
    } else {
      setError(data.message || 'Card payment initiation failed')
      setPaying(false)
    }
  }

  const startPolling = (paymentId: string) => {
    const interval = setInterval(async () => {
      const res = await apiFetch(`/api/payments/status/${paymentId}/`)
      if (res.ok) {
        const data = await res.json()
        if (data.status === 'completed' && data.credits_added) {
          clearInterval(interval)
          setPollInterval(null)
          setPaying(false)
          setPaymentStatus('')
          await loadData()
          router.push(`/payments/success?payment_id=${paymentId}`)
        } else if (data.status === 'failed' || data.status === 'cancelled') {
          clearInterval(interval)
          setPollInterval(null)
          setPaying(false)
          setPaymentStatus('')
          setError('Payment was not completed. Please try again.')
        }
      }
    }, 3000)
    setPollInterval(interval)

    // Stop polling after 3 minutes
    setTimeout(() => {
      clearInterval(interval)
      if (paying) {
        setPaying(false)
        setPaymentStatus('')
        setError('Payment timed out. If you paid, please contact support.')
      }
    }, 180000)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-5xl mx-auto px-4 py-6 flex items-center justify-between">
          <div>
            <Link href="/dashboard" className="text-gray-500 hover:text-gray-900 text-sm">← Dashboard</Link>
            <h1 className="text-2xl font-bold text-gray-900 mt-1">Buy Tokens</h1>
          </div>
          {balance && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 text-center">
              <p className="text-xs text-blue-600 font-medium">Current Balance</p>
              <p className="text-2xl font-bold text-blue-700">{balance.balance}</p>
              <p className="text-xs text-blue-500">credits</p>
            </div>
          )}
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Token Packs */}
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Select a Token Pack</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {packs.map((pack) => (
            <div
              key={pack.id}
              onClick={() => { setSelectedPack(pack); setError('') }}
              className={`relative bg-white rounded-xl border-2 p-5 cursor-pointer transition-all ${
                selectedPack?.id === pack.id
                  ? 'border-blue-500 shadow-md'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              {pack.is_featured && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs px-3 py-1 rounded-full">
                  Most Popular
                </span>
              )}
              <h3 className="font-bold text-gray-900 text-lg">{pack.name}</h3>
              <p className="text-3xl font-bold text-blue-600 mt-2">{pack.credits}</p>
              <p className="text-sm text-gray-500">credits</p>
              <p className="text-lg font-semibold text-gray-900 mt-3">KES {pack.price_kes.toLocaleString()}</p>
              <p className="text-xs text-gray-500 mt-1">{pack.description}</p>
              {selectedPack?.id === pack.id && (
                <div className="absolute top-3 right-3 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* What You Get */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-8">
          <h3 className="font-semibold text-gray-900 mb-3">What credits are used for:</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm text-gray-600">
            {[
              { label: 'Write CV from scratch', cost: 50 },
              { label: 'Revamp existing CV', cost: 30 },
              { label: 'Customize CV for job', cost: 20 },
              { label: 'Write cover letter', cost: 20 },
              { label: 'Career guidance (per message)', cost: 10 },
              { label: 'Job matching', cost: 5 },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                <span>{item.label}</span>
                <span className="font-semibold text-blue-600 ml-2">{item.cost}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Payment Method */}
        {selectedPack && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Pay KES {selectedPack.price_kes.toLocaleString()} for {selectedPack.credits} credits
            </h2>

            {/* Payment method tabs */}
            <div className="flex gap-3 mb-6">
              <button
                onClick={() => setPaymentMethod('mpesa')}
                className={`flex-1 py-3 rounded-lg font-medium border-2 transition-colors ${
                  paymentMethod === 'mpesa'
                    ? 'border-green-500 bg-green-50 text-green-700'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                M-Pesa
              </button>
              <button
                onClick={() => setPaymentMethod('card')}
                className={`flex-1 py-3 rounded-lg font-medium border-2 transition-colors ${
                  paymentMethod === 'card'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                Visa / Mastercard
              </button>
            </div>

            {paymentMethod === 'mpesa' ? (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  M-Pesa Phone Number
                </label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="e.g. 0712 345 678"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent text-lg"
                  disabled={paying}
                />
                <p className="text-sm text-gray-500 mt-2">
                  You will receive an STK Push prompt on your phone. Enter your PIN to complete payment.
                </p>

                {paymentStatus && (
                  <div className="mt-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center gap-3">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-green-600" />
                    {paymentStatus}
                  </div>
                )}

                <button
                  onClick={handleMpesaPay}
                  disabled={paying || !phone.trim()}
                  className="mt-4 w-full bg-green-600 text-white py-4 rounded-lg font-bold text-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {paying ? 'Processing...' : `Pay KES ${selectedPack.price_kes.toLocaleString()} via M-Pesa`}
                </button>
              </div>
            ) : (
              <div>
                <p className="text-gray-600 mb-4">
                  You will be redirected to a secure payment page to enter your card details.
                  Supports Visa, Mastercard, and other major cards.
                </p>
                <button
                  onClick={handleCardPay}
                  disabled={paying}
                  className="w-full bg-blue-600 text-white py-4 rounded-lg font-bold text-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {paying ? 'Redirecting...' : `Pay KES ${selectedPack.price_kes.toLocaleString()} by Card`}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Transaction History */}
        {balance && balance.recent_transactions.length > 0 && (
          <div className="mt-8 bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-4">Recent Transactions</h3>
            <div className="space-y-2">
              {balance.recent_transactions.map((tx, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{tx.description}</p>
                    <p className="text-xs text-gray-500">{new Date(tx.date).toLocaleString()}</p>
                  </div>
                  <span className={`font-semibold text-sm ${tx.credits > 0 ? 'text-green-600' : 'text-red-500'}`}>
                    {tx.credits > 0 ? '+' : ''}{tx.credits}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
