import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import toast from 'react-hot-toast'

// Types
interface ApiError {
  message?: string
  error?: string
  code?: string
  details?: Record<string, any>
  [key: string]: any  // Allow additional properties
}

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000, // 30 second timeout
})

// Request interceptor - Add auth token and logging
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add auth token
    if (typeof window !== 'undefined') {
      const access = localStorage.getItem('access_token')
      if (access && config.headers) {
        config.headers.Authorization = `Bearer ${access}`
      }
    }

    // Log requests in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
        data: config.data,
        params: config.params,
      })
    }

    return config
  },
  (error: AxiosError) => {
    console.error('[API Request Error]', error)
    return Promise.reject(error)
  }
)

// Response interceptor - Handle errors, token refresh, and logging
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Log successful responses in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, {
        status: response.status,
        data: response.data,
      })
    }
    return response
  },
  async (error: AxiosError<ApiError>) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // Log errors
    if (process.env.NODE_ENV === 'development') {
      console.error('[API Error]', {
        url: original?.url,
        status: error.response?.status,
        message: error.response?.data?.message || error.message,
      })
    }

    // Handle 401 - Token refresh
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true

      try {
        const refresh = localStorage.getItem('refresh_token')
        if (!refresh) {
          throw new Error('No refresh token available')
        }

        const response = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/auth/token/refresh/`,
          { refresh }
        )

        // Store new access token
        localStorage.setItem('access_token', response.data.access)

        // Update authorization header
        if (original.headers) {
          original.headers.Authorization = `Bearer ${response.data.access}`
        }

        // Retry original request
        return api(original)
      } catch (refreshError) {
        // Refresh failed - clear tokens and redirect to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        
        // Show toast before redirecting
        toast.error('Session expired. Please log in again.')
        
        // Only redirect if we're in a browser
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
        
        return Promise.reject(refreshError)
      }
    }

    // Format error message
    const errorMessage = error.response?.data?.message || 
                        error.response?.data?.error || 
                        error.message || 
                        'An unexpected error occurred'

    // Show toast for non-401 errors (401 is handled above)
    if (error.response?.status !== 401) {
      // Don't toast for 404 on specific routes or validation errors
      if (error.response?.status !== 404 && !original.url?.includes('validate')) {
        toast.error(errorMessage)
      }
    }

    return Promise.reject({
      ...error,
      userMessage: errorMessage,
      status: error.response?.status,
      data: error.response?.data,
    })
  }
)

// Helper functions for common API operations
export const apiHelper = {
  get: <T = any>(url: string, config?: any) => api.get<T>(url, config),
  post: <T = any>(url: string, data?: any, config?: any) => api.post<T>(url, data, config),
  put: <T = any>(url: string, data?: any, config?: any) => api.put<T>(url, data, config),
  patch: <T = any>(url: string, data?: any, config?: any) => api.patch<T>(url, data, config),
  delete: <T = any>(url: string, config?: any) => api.delete<T>(url, config),
}

export default api
