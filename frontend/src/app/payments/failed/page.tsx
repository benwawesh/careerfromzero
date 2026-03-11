'use client'

import Link from 'next/link'

export default function PaymentFailedPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-lg p-10 max-w-md w-full text-center">
        <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <svg className="w-10 h-10 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Payment Failed</h1>
        <p className="text-gray-600 mb-6">
          Your payment was not completed. No charges were made to your account.
        </p>
        <div className="flex flex-col gap-3">
          <Link href="/payments" className="bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700">
            Try Again
          </Link>
          <Link href="/dashboard" className="border border-gray-300 text-gray-700 py-3 rounded-lg font-semibold hover:bg-gray-50">
            Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}
