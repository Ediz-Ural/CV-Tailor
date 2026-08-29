import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, UNAUTHORIZED_EVENT, api } from '@/lib/api'
import { clearAccessToken, getAccessToken, setAccessToken } from '@/lib/auth'

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('api client', () => {
  beforeEach(() => {
    clearAccessToken()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    clearAccessToken()
  })

  it('sends the stored access token as a bearer header', async () => {
    setAccessToken('token-123')
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 'user-1' }))
    vi.stubGlobal('fetch', fetchMock)

    await api.get('/me')

    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer token-123')
  })

  it('authenticates blob downloads too', async () => {
    // The archive used to link straight to the download URL, which dropped the
    // header and always came back 401.
    setAccessToken('token-123')
    const fetchMock = vi.fn().mockResolvedValue(new Response(new Blob(['pdf']), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await api.blob('/generated-cvs/abc/download')

    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer token-123')
  })

  it('clears the session and announces it when an authenticated call is rejected', async () => {
    setAccessToken('expired-token')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'Not authenticated' }, 401)))
    const expired = vi.fn()
    window.addEventListener(UNAUTHORIZED_EVENT, expired)

    await expect(api.get('/me')).rejects.toBeInstanceOf(ApiError)

    expect(getAccessToken()).toBeNull()
    expect(expired).toHaveBeenCalledOnce()
    window.removeEventListener(UNAUTHORIZED_EVENT, expired)
  })

  it('leaves an anonymous 401 alone so a bad login is just an error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'Email veya parola hatali' }, 401)))
    const expired = vi.fn()
    window.addEventListener(UNAUTHORIZED_EVENT, expired)

    await expect(api.post('/auth/login', { email: 'a@b.co', password: 'nope' })).rejects.toMatchObject({
      detail: 'Email veya parola hatali',
    })

    expect(expired).not.toHaveBeenCalled()
    window.removeEventListener(UNAUTHORIZED_EVENT, expired)
  })

  it('flattens validation error details into one message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: [{ msg: 'alan zorunlu' }, { msg: 'cok kisa' }] }, 422)))

    await expect(api.post('/pool-items', {})).rejects.toMatchObject({
      detail: 'alan zorunlu, cok kisa',
      status: 422,
    })
  })
})
