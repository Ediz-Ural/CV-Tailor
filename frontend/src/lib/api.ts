const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

import { clearAccessToken, getAccessToken } from '@/lib/auth'

export const UNAUTHORIZED_EVENT = 'cv-tailor:unauthorized'

export class ApiError extends Error {
  readonly status: number
  readonly detail: string

  constructor(detail: string, status: number) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function readErrorDetail(payload: unknown, status: number) {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (item && typeof item === 'object' && 'msg' in item ? String(item.msg) : String(item)))
        .join(', ')
    }
  }
  return `API istegi ${status} durumuyla basarisiz oldu`
}

function handleUnauthorized(status: number, hadToken: boolean) {
  // Access tokens expire after 30 minutes and there is no refresh flow, so a 401
  // on a request we authenticated means the session is over.
  if (status !== 401 || !hadToken) return
  clearAccessToken()
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAccessToken()
  const response = await fetch(`${API_URL}${path.startsWith('/') ? path : `/${path}`}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    handleUnauthorized(response.status, Boolean(token))
    const payload: unknown = await response.json().catch(() => null)
    throw new ApiError(readErrorDetail(payload, response.status), response.status)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const token = getAccessToken()
  const response = await fetch(`${API_URL}${path.startsWith('/') ? path : `/${path}`}`, {
    ...init,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    handleUnauthorized(response.status, Boolean(token))
    const payload: unknown = await response.json().catch(() => null)
    throw new ApiError(readErrorDetail(payload, response.status), response.status)
  }

  return response.blob()
}

export const api = {
  get<T>(path: string, init?: RequestInit) {
    return request<T>(path, { ...init, method: 'GET' })
  },
  post<T>(path: string, body?: unknown, init?: RequestInit) {
    return request<T>(path, {
      ...init,
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...init?.headers },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  },
  put<T>(path: string, body: unknown, init?: RequestInit) {
    return request<T>(path, {
      ...init,
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...init?.headers },
      body: JSON.stringify(body),
    })
  },
  form<T>(path: string, body: FormData, init?: RequestInit) {
    return request<T>(path, {
      ...init,
      method: 'POST',
      body,
    })
  },
  blob(path: string, init?: RequestInit) {
    return requestBlob(path, { ...init, method: 'GET' })
  },
  delete<T>(path: string, body?: unknown, init?: RequestInit) {
    return request<T>(path, {
      ...init,
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json', ...init?.headers },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  },
}
