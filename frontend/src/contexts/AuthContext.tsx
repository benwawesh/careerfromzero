'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'

interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  is_staff: boolean
  is_superuser: boolean
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (usernameOrEmail: string, password: string) => Promise<User>
  logout: () => void
  isAuthenticated: boolean
  isAdmin: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    // Check if user is logged in on mount
    const checkAuth = () => {
      const userStr = localStorage.getItem('user')
      const token = localStorage.getItem('access_token')
      
      if (userStr && token) {
        try {
          setUser(JSON.parse(userStr))
        } catch (error) {
          console.error('Error parsing user data:', error)
          localStorage.removeItem('user')
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        }
      }
      setLoading(false)
    }

    checkAuth()
  }, [])

  const login = async (usernameOrEmail: string, password: string): Promise<User> => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: usernameOrEmail, password }),
      })

      const data = await response.json()

      if (response.ok) {
        localStorage.setItem('access_token', data.access)
        localStorage.setItem('refresh_token', data.refresh)
        localStorage.setItem('user', JSON.stringify(data.user))
        setUser(data.user)
        toast.success('Successfully logged in!')
        return data.user
      } else {
        const errorMessage = data.error || data.message || 'Login failed'
        toast.error(errorMessage)
        throw new Error(errorMessage)
      }
    } catch (error: any) {
      const message = error.message || 'Login failed. Please try again.'
      toast.error(message)
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    setUser(null)
    toast.success('Successfully logged out')
    router.push('/login')
  }

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
    isAdmin: user?.is_staff || false,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}