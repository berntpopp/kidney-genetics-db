export interface User {
  id: number
  email: string
  username: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export type UserRole = 'admin' | 'curator' | 'public'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
}
