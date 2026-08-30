import { type FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ShieldCheck } from 'lucide-react'

import { Field } from '@/components/Field'
import { WorkspaceShell } from '@/components/WorkspaceShell'
import { ApiError, api } from '@/lib/api'
import { errorMessage } from '@/lib/view'
import type { Profile, ProfileForm, User } from '@/types'

const emptyProfile: ProfileForm = {
  fullName: '',
  email: '',
  phone: '',
  location: '',
  school: '',
  degree: '',
  summary: '',
}

export function ProfilePage({ onLogout }: { onLogout: () => void }) {
  const { t } = useTranslation()
  const [user, setUser] = useState<User | null>(null)
  const [form, setForm] = useState<ProfileForm>(emptyProfile)
  const [exists, setExists] = useState(false)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.allSettled([api.get<User>('/me'), api.get<Profile>('/profile')]).then(([meResult, profileResult]) => {
      if (meResult.status === 'rejected') { onLogout(); return }
      setUser(meResult.value)
      if (profileResult.status === 'fulfilled') {
        const profile = profileResult.value
        setExists(true)
        setForm({
          fullName: profile.full_name,
          email: profile.contact?.email ?? meResult.value.email,
          phone: profile.contact?.phone ?? '', location: profile.contact?.location ?? '',
          school: profile.education[0]?.school ?? '', degree: profile.education[0]?.degree ?? '',
          summary: profile.personal_info?.summary ?? '',
        })
      } else if (profileResult.reason instanceof ApiError && profileResult.reason.status === 404) {
        setForm((current) => ({ ...current, email: meResult.value.email }))
      } else { setError(errorMessage(profileResult.reason)) }
      setLoading(false)
    })
  }, [onLogout])

  function update(field: keyof ProfileForm, value: string) { setForm((current) => ({ ...current, [field]: value })) }

  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setMessage('')
    const payload = {
      full_name: form.fullName,
      contact: { email: form.email, phone: form.phone, location: form.location },
      education: form.school || form.degree ? [{ school: form.school, degree: form.degree }] : [],
      personal_info: { summary: form.summary },
    }
    try {
      if (exists) await api.put<Profile>('/profile', payload)
      else { await api.post<Profile>('/profile', payload); setExists(true) }
      setMessage(t('common.savedProfile'))
    } catch (caught) { setError(errorMessage(caught)) } finally { setBusy(false) }
  }

  return <WorkspaceShell eyebrow={t('profile.eyebrow')} onLogout={onLogout} route="/profile" title={t('profile.title')} userEmail={user?.email}>
    <main className="mx-auto max-w-5xl px-5 py-10 sm:px-8">
      <div className="mb-8 flex items-start gap-4"><span className="grid size-11 place-items-center rounded-xl border bg-primary/10 text-primary"><ShieldCheck className="size-5" /></span><div><h2 className="text-3xl font-semibold tracking-tight">{t('profile.heading')}</h2><p className="mt-2 text-sm text-muted-foreground">{t('profile.description')}</p></div></div>
      {loading ? <p className="text-sm text-muted-foreground">{t('common.loadingProfile')}</p> : <form className="rounded-xl border bg-card/90 p-5 shadow-xl shadow-black/10 sm:p-7" onSubmit={save}>
        <div className="grid gap-5 sm:grid-cols-2"><Field label={t('profile.fullName')} onChange={(event) => update('fullName', event.target.value)} required value={form.fullName} /><Field label={t('common.email')} onChange={(event) => update('email', event.target.value)} required type="email" value={form.email} /><Field label={t('profile.phone')} onChange={(event) => update('phone', event.target.value)} value={form.phone} /><Field label={t('profile.location')} onChange={(event) => update('location', event.target.value)} value={form.location} /><Field label={t('profile.school')} onChange={(event) => update('school', event.target.value)} value={form.school} /><Field label={t('profile.degree')} onChange={(event) => update('degree', event.target.value)} value={form.degree} /></div>
        <label className="mt-5 block text-sm font-medium">{t('profile.summary')}<textarea className="mt-2 min-h-28 w-full rounded-lg border bg-background p-3 text-sm" onChange={(event) => update('summary', event.target.value)} value={form.summary} /></label>
        {error && <p className="mt-5 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>}{message && <p className="mt-5 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">{message}</p>}
        <div className="mt-6 flex justify-end"><button className="h-11 rounded-lg bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-60" disabled={busy} type="submit">{busy ? t('common.saving') : exists ? t('common.saveChanges') : t('common.createProfile')}</button></div>
      </form>}
    </main>
  </WorkspaceShell>
}
