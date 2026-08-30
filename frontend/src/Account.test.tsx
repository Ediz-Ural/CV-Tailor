import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import '@/i18n'
import { clearAccessToken, setAccessToken } from '@/lib/auth'

const user = { id: 'user-1', email: 'ada@example.test', kvkk_consent_at: '2026-06-21T00:00:00Z' }
const notice = { version: '2026-06-21', title: 'KVKK', explicit_consent_text: 'metin', sections: [] }

type Stub = { body: unknown; status?: number }

function stubRoutes(routes: Record<string, Stub>) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input), 'http://localhost').pathname
    const route = routes[path]
    if (!route) return new Response(JSON.stringify({ detail: `no stub for ${path}` }), { status: 404 })
    return new Response(JSON.stringify(route.body), {
      status: route.status ?? 200,
      headers: { 'Content-Type': 'application/json' },
    })
  })
}

describe('account screen', () => {
  beforeEach(() => {
    setAccessToken('token-123')
    window.history.replaceState({}, '', '/account')
  })

  afterEach(() => {
    clearAccessToken()
    vi.restoreAllMocks()
    window.history.replaceState({}, '', '/')
  })

  it('tells a new account that generation needs their own key', async () => {
    vi.stubGlobal('fetch', stubRoutes({
      '/me': { body: user },
      '/kvkk/aydinlatma': { body: notice },
      '/llm-credential': { body: { detail: 'yok' }, status: 404 },
    }))

    render(<App />)

    // A missing key is the normal state for a new account, not an error.
    expect(await screen.findByText(/anahtar eklemedin|No key added yet/i)).toBeInTheDocument()
  })

  it('shows which key is stored without ever revealing it', async () => {
    const credential = { provider: 'openai', model: 'gpt-4o-mini', key_hint: '4321', updated_at: '2026-08-30T00:00:00Z' }
    vi.stubGlobal('fetch', stubRoutes({
      '/me': { body: user },
      '/kvkk/aydinlatma': { body: notice },
      '/llm-credential': { body: credential },
    }))

    render(<App />)

    expect(await screen.findByText(/4321/)).toBeInTheDocument()
    expect(screen.getByText(/gpt-4o-mini/)).toBeInTheDocument()
  })

  it('sends the key to the API and clears the input afterwards', async () => {
    const fetchMock = stubRoutes({
      '/me': { body: user },
      '/kvkk/aydinlatma': { body: notice },
      '/llm-credential': { body: { detail: 'yok' }, status: 404 },
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    const keyInput = (await screen.findByLabelText(/API anahtar[ıi]|API key/i)) as HTMLInputElement

    // The key must never be a plain-text field on screen.
    expect(keyInput.type).toBe('password')

    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), 'http://localhost').pathname
      if (path === '/llm-credential' && init?.method === 'PUT') {
        return new Response(
          JSON.stringify({ provider: 'openai', model: 'gpt-4o-mini', key_hint: '9999', updated_at: '2026-08-30T00:00:00Z' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        )
      }
      return new Response(JSON.stringify({ detail: 'yok' }), { status: 404 })
    })

    keyInput.focus()
    const form = keyInput.closest('form')
    expect(form).not.toBeNull()

    const { fireEvent } = await import('@testing-library/react')
    fireEvent.change(keyInput, { target: { value: 'sk-brand-new-9999' } })
    fireEvent.submit(form as HTMLFormElement)

    await waitFor(() => expect(screen.getByText(/9999/)).toBeInTheDocument())
    expect((screen.getByLabelText(/API anahtar[ıi]|API key/i) as HTMLInputElement).value).toBe('')
  })
})
