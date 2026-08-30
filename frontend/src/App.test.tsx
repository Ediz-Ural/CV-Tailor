import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import '@/i18n'
import { clearAccessToken, setAccessToken } from '@/lib/auth'

type Route = { body: unknown; status?: number }

function routeResponses(routes: Record<string, Route>) {
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

const user = { id: 'user-1', email: 'ada@example.test', kvkk_consent_at: '2026-06-21T00:00:00Z' }

describe('pool screen', () => {
  beforeEach(() => {
    setAccessToken('token-123')
    window.history.replaceState({}, '', '/pool')
  })

  afterEach(() => {
    clearAccessToken()
    vi.restoreAllMocks()
    window.history.replaceState({}, '', '/')
  })

  it('reports a successful GitHub connection carried back on the URL', async () => {
    // The backend redirects here after OAuth instead of rendering a JSON body.
    window.history.replaceState({}, '', '/pool?github=connected&username=octocat')
    vi.stubGlobal('fetch', routeResponses({
      '/me': { body: user },
      '/pool-items': { body: [] },
      '/pool/pending': { body: [] },
    }))

    render(<App />)

    // Both the banner and the sync log mention the account.
    expect(await screen.findAllByText(/octocat/)).not.toHaveLength(0)
    // The parameters are consumed so a refresh does not replay the message.
    await waitFor(() => expect(window.location.search).toBe(''))
  })

  it('explains a failed GitHub connection instead of showing a raw error', async () => {
    window.history.replaceState({}, '', '/pool?github=error&reason=not_configured')
    vi.stubGlobal('fetch', routeResponses({
      '/me': { body: user },
      '/pool-items': { body: [] },
      '/pool/pending': { body: [] },
    }))

    render(<App />)

    expect(await screen.findByText(/OAuth/)).toBeInTheDocument()
  })

  it('offers edit and delete controls on a pool item', async () => {
    vi.stubGlobal('fetch', routeResponses({
      '/me': { body: user },
      '/pool/pending': { body: [] },
      '/pool-items': {
        body: [{
          id: 'item-1',
          user_id: user.id,
          source: 'manual',
          type: 'experience',
          title: 'FastAPI servisleri',
          raw_content: 'Odeme servisini kurdum.',
          tags: ['backend'],
          technologies: ['FastAPI'],
          language: 'tr',
          verified_by_user: true,
          created_at: '2026-06-21T00:00:00Z',
          embedding_dimensions: 1024,
        }],
      },
    }))

    render(<App />)

    expect(await screen.findByRole('button', { name: /d[üu]zenle|edit/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sil|delete/i })).toBeInTheDocument()
  })
})
