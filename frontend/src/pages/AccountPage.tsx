import { type FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { KeyRound, Loader2, Settings, ShieldCheck, Trash2 } from 'lucide-react'

import { Field } from '@/components/Field'
import { WorkspaceShell } from '@/components/WorkspaceShell'
import { ApiError, api } from '@/lib/api'
import { errorMessage } from '@/lib/view'
import type { KVKKNotice, LLMCredential, User } from '@/types'

const DELETE_ACCOUNT_CONFIRMATION = 'HESABIMI SIL'

export function AccountPage({ onLogout }: { onLogout: () => void }) {
  const { t } = useTranslation()
  const [user, setUser] = useState<User | null>(null)
  const [notice, setNotice] = useState<KVKKNotice | null>(null)
  const [credential, setCredential] = useState<LLMCredential | null>(null)
  const [keyForm, setKeyForm] = useState({ provider: 'openai', model: 'gpt-4o-mini', apiKey: '' })
  const [keyBusy, setKeyBusy] = useState(false)
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.allSettled([
      api.get<User>('/me'),
      api.get<KVKKNotice>('/kvkk/aydinlatma'),
      api.get<LLMCredential>('/llm-credential'),
    ]).then(([meResult, noticeResult, credentialResult]) => {
      if (meResult.status === 'rejected') {
        if (meResult.reason instanceof ApiError && meResult.reason.status === 401) onLogout()
        else setError(errorMessage(meResult.reason))
        return
      }
      setUser(meResult.value)
      if (noticeResult.status === 'fulfilled') setNotice(noticeResult.value)
      // A missing key is the normal state for a new account, not an error.
      if (credentialResult.status === 'fulfilled') {
        setCredential(credentialResult.value)
        setKeyForm((current) => ({ ...current, provider: credentialResult.value.provider, model: credentialResult.value.model }))
      }
    })
  }, [onLogout])

  async function saveKey(event: FormEvent) {
    event.preventDefault()
    setKeyBusy(true); setError(''); setMessage('')
    try {
      const saved = await api.put<LLMCredential>('/llm-credential', {
        provider: keyForm.provider,
        model: keyForm.model,
        api_key: keyForm.apiKey,
      })
      setCredential(saved)
      setKeyForm((current) => ({ ...current, apiKey: '' }))
      setMessage(t('account.keySaved'))
    } catch (caught) { setError(errorMessage(caught)) } finally { setKeyBusy(false) }
  }

  async function removeKey() {
    setKeyBusy(true); setError(''); setMessage('')
    try {
      await api.delete('/llm-credential')
      setCredential(null)
      setMessage(t('account.keyRemoved'))
    } catch (caught) { setError(errorMessage(caught)) } finally { setKeyBusy(false) }
  }

  const canDelete = confirmation.trim() === DELETE_ACCOUNT_CONFIRMATION

  async function remove(event: FormEvent) {
    event.preventDefault()
    if (!canDelete) { setError(t('account.deleteMismatch')); return }
    setBusy(true); setError('')
    try {
      await api.delete('/account', { confirmation: DELETE_ACCOUNT_CONFIRMATION })
      onLogout()
    } catch (caught) { setError(errorMessage(caught)); setBusy(false) }
  }

  return <WorkspaceShell eyebrow={t('account.eyebrow')} onLogout={onLogout} route="/account" title={t('account.title')} userEmail={user?.email}>
    <main className="mx-auto max-w-4xl px-5 py-10 sm:px-8">
      <div className="mb-8 flex items-start gap-4">
        <span className="grid size-11 place-items-center rounded-xl border bg-primary/10 text-primary"><Settings className="size-5" /></span>
        <div>
          <h2 className="text-3xl font-semibold tracking-tight">{t('account.heading')}</h2>
          <p className="mt-2 text-sm text-muted-foreground">{t('account.description')}</p>
        </div>
      </div>

      {error && <p className="mb-5 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>}
      {message && <p className="mb-5 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">{message}</p>}

      {notice && <section className="mb-5 rounded-xl border bg-card/90 p-5">
        <div className="flex items-center gap-2"><ShieldCheck className="size-4 text-primary" /><h3 className="text-sm font-semibold">{t('account.noticeTitle')}</h3></div>
        <p className="mt-1 font-mono text-[11px] text-muted-foreground">{t('auth.version', { version: notice.version })}</p>
        <div className="mt-4 max-h-64 space-y-3 overflow-auto text-sm leading-6">
          {notice.sections.map((section) => <article key={section.title}>
            <h4 className="font-medium">{section.title}</h4>
            <p className="mt-1 text-muted-foreground">{section.body}</p>
          </article>)}
        </div>
      </section>}

      <section className="mb-5 rounded-xl border bg-card/90 p-5">
        <div className="flex items-center gap-2"><KeyRound className="size-4 text-primary" /><h3 className="text-sm font-semibold">{t('account.keyTitle')}</h3></div>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{t('account.keyDescription')}</p>

        <p className={`mt-4 rounded-lg border px-3 py-2 text-sm ${credential ? 'border-success/30 bg-success/10 text-success' : 'border-warning/30 bg-warning/10 text-warning'}`}>
          {credential
            ? t('account.keyStored', { provider: credential.provider, model: credential.model, hint: credential.key_hint })
            : t('account.keyMissing')}
        </p>

        <form className="mt-5 space-y-4" onSubmit={saveKey}>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm font-medium">{t('account.keyProvider')}
              <select className="mt-2 h-11 w-full rounded-lg border bg-background px-3 text-sm" onChange={(event) => setKeyForm((current) => ({ ...current, provider: event.target.value, model: event.target.value === 'anthropic' ? 'claude-sonnet-4-5' : 'gpt-4o-mini' }))} value={keyForm.provider}>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
              </select>
            </label>
            <Field label={t('account.keyModel')} onChange={(event) => setKeyForm((current) => ({ ...current, model: event.target.value }))} required value={keyForm.model} />
          </div>
          <Field autoComplete="off" label={t('account.keyValue')} onChange={(event) => setKeyForm((current) => ({ ...current, apiKey: event.target.value }))} placeholder="sk-..." required type="password" value={keyForm.apiKey} />
          <p className="text-xs leading-5 text-muted-foreground">{t('account.keyHelp')}</p>
          <div className="flex flex-wrap gap-3">
            <button className="flex h-11 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-60" disabled={keyBusy || !keyForm.apiKey.trim()} type="submit">
              {keyBusy ? <Loader2 className="size-4 animate-spin" /> : <KeyRound className="size-4" />}{keyBusy ? t('account.keySaving') : t('account.keySave')}
            </button>
            {credential && <button className="flex h-11 items-center gap-2 rounded-lg border border-danger/30 px-5 text-sm text-danger hover:bg-danger/10 disabled:opacity-50" disabled={keyBusy} onClick={() => void removeKey()} type="button"><Trash2 className="size-4" />{t('account.keyDelete')}</button>}
          </div>
        </form>
      </section>

      <section className="rounded-xl border border-danger/30 bg-danger/5 p-5">
        <div className="flex items-center gap-2"><Trash2 className="size-4 text-danger" /><h3 className="text-sm font-semibold text-danger">{t('account.deleteTitle')}</h3></div>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{t('account.deleteDescription')}</p>
        <form className="mt-5 space-y-4" onSubmit={remove}>
          <Field label={t('account.deleteConfirmLabel', { phrase: DELETE_ACCOUNT_CONFIRMATION })} onChange={(event) => setConfirmation(event.target.value)} placeholder={DELETE_ACCOUNT_CONFIRMATION} value={confirmation} />
          <button className="flex h-11 items-center justify-center gap-2 rounded-lg bg-danger px-5 text-sm font-semibold text-white disabled:opacity-50" disabled={busy || !canDelete} type="submit">
            {busy ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}{busy ? t('account.deleteBusy') : t('account.deleteSubmit')}
          </button>
        </form>
      </section>
    </main>
  </WorkspaceShell>
}
