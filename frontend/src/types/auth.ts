export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  phone_number: string | null
  bio: string | null
  location: string | null
  linkedin_url: string | null
  github_url: string | null
  portfolio_url: string | null
  job_search_preferences: Record<string, unknown>
  career_goals: string | null
  profile_picture: string | null
  created_at: string
  updated_at: string
}

export interface AuthTokens {
  access: string
  refresh: string
}

export interface LoginResponse extends AuthTokens {
  user: User
}
