/**
 * Authenticated fetch wrapper with automatic JWT token refresh.
 *
 * On any 401 response it tries POST /api/auth/token/refresh/ once.
 * If the refresh succeeds the original request is retried with the new token.
 * If the refresh fails (expired/blacklisted) the user is logged out and
 * redirected to /login.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || ''

async function refreshAccessToken(): Promise<string | null> {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) return null

  const res = await fetch(`${API_URL}/api/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })

  if (!res.ok) {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    window.location.href = '/login'
    return null
  }

  const data = await res.json()
  localStorage.setItem('access_token', data.access)
  if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
  return data.access
}

export async function streamFetch(
  path: string,
  body: object,
  onToken: (token: string) => void,
  onDone: (data: Record<string, unknown>) => void,
  onError?: (msg: string) => void,
): Promise<void> {
  const token = localStorage.getItem('access_token')
  const API_URL = process.env.NEXT_PUBLIC_API_URL || ''

  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })

  if (!res.ok || !res.body) {
    onError?.(`Request failed: ${res.status}`)
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const data = JSON.parse(line.slice(6))
        if (data.type === 'text') onToken(data.content)
        else if (data.type === 'done') onDone(data)
        else if (data.type === 'error') onError?.(data.message)
      } catch {}
    }
  }
}

export async function apiFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem('access_token')

  const makeRequest = (t: string | null) =>
    fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...(options.headers || {}),
        ...(t ? { Authorization: `Bearer ${t}` } : {}),
      },
    })

  const res = await makeRequest(token)

  if (res.status !== 401) return res

  // Try to refresh once
  const newToken = await refreshAccessToken()
  if (!newToken) return res // redirect already triggered

  return makeRequest(newToken)
}
