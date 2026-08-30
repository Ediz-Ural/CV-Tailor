import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AuthShell } from '@/components/AuthShell'
import { Field } from '@/components/Field'
import { api } from '@/lib/api'
import { setAccessToken } from '@/lib/auth'
import { navigate } from '@/lib/routing'
import { errorMessage } from '@/lib/view'

export function Login({ onAuthenticated }: { onAuthenticated: () => void }) {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const token = await api.post<{ access_token: string }>('/auth/login', { email, password })
      setAccessToken(token.access_token)
      onAuthenticated()
    } catch (caught) { setError(errorMessage(caught)) } finally { setBusy(false) }
  }

  return <AuthShell eyebrow={t('auth.loginEyebrow')} title={t('auth.loginTitle')} description={t('auth.loginDescription')}>
    <form className="mt-8 space-y-5" onSubmit={submit}>
      <Field autoComplete="email" label={t('common.email')} onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
      <Field autoComplete="current-password" label={t('common.password')} minLength={8} onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
      {error && <p className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>}
      <button className="h-11 w-full rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground transition-opacity disabled:opacity-60" disabled={busy} type="submit">{busy ? t('auth.loginBusy') : t('auth.loginSubmit')}</button>
    </form>
    <p className="mt-6 text-center text-sm text-muted-foreground">{t('auth.noAccount')} <button className="font-medium text-primary" onClick={() => navigate('/register')} type="button">{t('auth.registerLink')}</button></p>
  </AuthShell>
}
