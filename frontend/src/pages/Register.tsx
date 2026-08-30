import { type FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ShieldCheck } from 'lucide-react'

import { AuthShell } from '@/components/AuthShell'
import { Field } from '@/components/Field'
import { api } from '@/lib/api'
import { navigate } from '@/lib/routing'
import { errorMessage } from '@/lib/view'
import type { KVKKNotice } from '@/types'

export function Register() {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [consent, setConsent] = useState(false)
  const [notice, setNotice] = useState<KVKKNotice | null>(null)
  const [noticeOpen, setNoticeOpen] = useState(false)
  const [noticeError, setNoticeError] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get<KVKKNotice>('/kvkk/aydinlatma')
      .then(setNotice)
      .catch((caught) => setNoticeError(errorMessage(caught)))
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      await api.post('/auth/register', { email, password, kvkk_consent: consent })
      navigate('/login')
    } catch (caught) { setError(errorMessage(caught)) } finally { setBusy(false) }
  }

  return <AuthShell eyebrow={t('auth.registerEyebrow')} title={t('auth.registerTitle')} description={t('auth.registerDescription')}>
    <form className="mt-8 space-y-5" onSubmit={submit}>
      <Field autoComplete="email" label={t('common.email')} onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
      <Field autoComplete="new-password" label={t('common.password')} minLength={8} onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
      <label className="flex items-start gap-3 rounded-lg border bg-background/60 p-3 text-sm leading-5">
        <input checked={consent} className="mt-1 size-4 accent-primary" onChange={(event) => setConsent(event.target.checked)} required type="checkbox" />
        <span><button className="text-left text-primary underline underline-offset-4" onClick={() => setNoticeOpen((current) => !current)} type="button">{t('auth.noticeButton')}</button> {t('auth.consentText')}</span>
      </label>
      {noticeOpen && <section className="max-h-72 overflow-auto rounded-lg border bg-background p-4 text-sm leading-6">
        {noticeError ? <p className="text-danger">{noticeError}</p> : notice ? <>
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold">{notice.title}</h2>
              <p className="mt-1 font-mono text-[11px] text-muted-foreground">{t('auth.version', { version: notice.version })}</p>
            </div>
            <ShieldCheck className="size-5 shrink-0 text-primary" />
          </div>
          <p className="mt-4 rounded-lg border border-primary/30 bg-primary/10 p-3 text-foreground">{notice.explicit_consent_text}</p>
          <div className="mt-4 space-y-3">
            {notice.sections.map((section) => <article key={section.title}>
              <h3 className="font-medium">{section.title}</h3>
              <p className="mt-1 text-muted-foreground">{section.body}</p>
            </article>)}
          </div>
        </> : <p className="text-muted-foreground">{t('auth.noticeLoading')}</p>}
      </section>}
      {error && <p className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>}
      <button className="h-11 w-full rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-60" disabled={busy || !consent} type="submit">{busy ? t('auth.registerBusy') : t('auth.registerLink')}</button>
    </form>
    <p className="mt-6 text-center text-sm text-muted-foreground">{t('auth.haveAccount')} <button className="font-medium text-primary" onClick={() => navigate('/login')} type="button">{t('auth.loginSubmit')}</button></p>
  </AuthShell>
}
