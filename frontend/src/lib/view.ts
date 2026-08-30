import { ApiError, api } from '@/lib/api'
import type { GithubCallback, Job } from '@/types'

export function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.detail : 'Beklenmeyen bir hata olustu.'
}

export async function downloadBlob(path: string, filename: string) {
  const blob = await api.blob(path)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function readGithubCallback(): GithubCallback | null {
  const params = new URLSearchParams(window.location.search)
  const outcome = params.get('github')
  if (!outcome) return null

  const callback: GithubCallback = outcome === 'connected'
    ? { status: 'connected', username: params.get('username') ?? '' }
    : { status: 'error', reason: params.get('reason') }
  // Drop the parameters so a refresh does not replay the message.
  window.history.replaceState({}, '', window.location.pathname)
  return callback
}

export function githubCallbackErrorKey(reason: string | null) {
  if (reason === 'not_configured') return 'pool.githubErrorNotConfigured'
  if (reason === 'github_unavailable') return 'pool.githubErrorUnavailable'
  return 'pool.githubErrorInvalidState'
}

export function jobLabel(job: Job) {
  const summary = job.parsed_requirements_json?.summary?.trim()
  if (summary) return summary.length > 120 ? `${summary.slice(0, 117)}...` : summary
  if (job.source_url) return job.source_url
  const firstLine = job.raw_text.split('\n').map((line) => line.trim()).find(Boolean) ?? ''
  return firstLine.length > 120 ? `${firstLine.slice(0, 117)}...` : firstLine
}

export function splitList(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}
