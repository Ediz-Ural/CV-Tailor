import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import {
  Check,
  CircleDot,
  Download,
  Eye,
  FileText,
  Filter,
  GitBranch,
  GitCompare,
  Layers3,
  LinkIcon,
  Library,
  Loader2,
  LogOut,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  Settings,
  ShieldCheck,
  Sparkles,
  Tags,
  Trash2,
  TriangleAlert,
  Trophy,
  Upload,
  UserRound,
  Wand2,
  X,
} from 'lucide-react'

import { ApiError, UNAUTHORIZED_EVENT, api } from '@/lib/api'
import { supportedLanguages } from '@/i18n'
import { TECH_TERMS } from '@/i18n/resources'
import { clearAccessToken, getAccessToken, setAccessToken } from '@/lib/auth'

type Route = '/login' | '/register' | '/profile' | '/pool' | '/generate' | '/archive' | '/account'
type PoolType = 'experience' | 'project' | 'skill' | 'education'
type PoolSource = 'pdf' | 'github' | 'manual'
type TypeFilter = 'all' | PoolType

type User = {
  id: string
  email: string
  kvkk_consent_at: string
}

type KVKKNotice = {
  version: string
  title: string
  explicit_consent_text: string
  sections: Array<{ title: string; body: string }>
}

type Profile = {
  id: string
  full_name: string
  contact: { email?: string; phone?: string; location?: string } | null
  education: Array<{ school?: string; degree?: string }>
  personal_info: { summary?: string } | null
}

type ProfileForm = {
  fullName: string
  email: string
  phone: string
  location: string
  school: string
  degree: string
  summary: string
}

type PoolItem = {
  id: string
  user_id: string
  source: PoolSource
  type: PoolType
  title: string | null
  raw_content: string
  tags: string[]
  technologies: string[]
  language: 'tr' | 'en' | 'mixed'
  verified_by_user: boolean
  created_at: string
  embedding_dimensions: number
}

type PoolForm = {
  type: PoolType
  title: string
  rawContent: string
  tags: string
  technologies: string
}

type PDFImportResponse = {
  imported_count: number
  items: PoolItem[]
  profile: Profile | null
}

type JobInputMode = 'text' | 'url'
type PipelineStepName = 'job_parser' | 'selector' | 'cvtailor' | 'evaluator' | 'typst_renderer'

type PipelineStep = {
  name: PipelineStepName
  status: 'pending' | 'running' | 'completed' | 'failed'
}

type BeforeAfterDiff = {
  source_pool_item_id: string
  title: string | null
  before: string
  after: string
  diff: string
}

type CVGenerationStatus = {
  pipeline_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  current_step: PipelineStepName | null
  steps: PipelineStep[]
  job_id: string | null
  generated_cv_id: string | null
  selected_pool_item_ids: string[]
  output_language: 'tr' | 'en' | 'mixed' | null
  job_summary: string | null
  ats_score: number | null
  missing_keywords: string[]
  ats_recommendations: string[]
  before_after_diff: BeforeAfterDiff[]
  error: string | null
}

type GeneratedCV = {
  id: string
  job_id: string
  output_language: 'tr' | 'en' | 'mixed'
  pdf_path: string | null
  ats_score: number | null
  created_at: string | null
}

const emptyProfile: ProfileForm = {
  fullName: '',
  email: '',
  phone: '',
  location: '',
  school: '',
  degree: '',
  summary: '',
}

const emptyPoolForm: PoolForm = {
  type: 'experience',
  title: '',
  rawContent: '',
  tags: '',
  technologies: '',
}

function routeFromPath(): Route {
  if (window.location.pathname === '/register') return '/register'
  if (window.location.pathname === '/profile') return '/profile'
  if (window.location.pathname === '/pool') return '/pool'
  if (window.location.pathname === '/generate') return '/generate'
  if (window.location.pathname === '/archive') return '/archive'
  if (window.location.pathname === '/account') return '/account'
  return '/login'
}

function navigate(path: Route, replace = false) {
  window.history[replace ? 'replaceState' : 'pushState']({}, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.detail : 'Beklenmeyen bir hata olustu.'
}

async function downloadBlob(path: string, filename: string) {
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

type GithubCallback = { status: 'connected'; username: string } | { status: 'error'; reason: string | null }

function readGithubCallback(): GithubCallback | null {
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

function githubCallbackErrorKey(reason: string | null) {
  if (reason === 'not_configured') return 'pool.githubErrorNotConfigured'
  if (reason === 'github_unavailable') return 'pool.githubErrorUnavailable'
  return 'pool.githubErrorInvalidState'
}

function splitList(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function LanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const currentLanguage = i18n.resolvedLanguage === 'en' ? 'en' : 'tr'

  return (
    <div aria-label={t('language.label')} className="flex rounded-lg border bg-background p-1">
      {supportedLanguages.map((language) => (
        <button
          aria-pressed={currentLanguage === language}
          className={`h-8 rounded-md px-3 font-mono text-xs ${currentLanguage === language ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-secondary'}`}
          key={language}
          onClick={() => void i18n.changeLanguage(language)}
          type="button"
        >
          {t(`language.${language}`)}
        </button>
      ))}
    </div>
  )
}

function AuthShell({ children, eyebrow, title, description }: { children: React.ReactNode; eyebrow: string; title: string; description: string }) {
  const { t } = useTranslation()

  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden px-5 py-12">
      <div className="pointer-events-none fixed inset-0 surface-grid opacity-40" />
      <motion.section
        animate={{ opacity: 1, y: 0 }}
        className="relative grid w-full max-w-5xl overflow-hidden rounded-2xl border bg-card/90 shadow-2xl shadow-black/25 backdrop-blur-xl lg:grid-cols-[1.05fr_0.95fr]"
        initial={{ opacity: 0, y: 14 }}
      >
        <div className="hidden border-r p-10 lg:flex lg:flex-col lg:justify-between">
          <div className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-lg bg-primary text-primary-foreground"><Sparkles className="size-4" /></span>
            <span className="font-semibold">{t('common.appName')}</span>
          </div>
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-primary">{t('auth.shellEyebrow')}</p>
            <p className="mt-4 text-4xl font-semibold tracking-tight">{t('auth.shellTitle')}</p>
            <p className="mt-5 text-sm leading-6 text-muted-foreground">{t('auth.shellDescription')}</p>
          </div>
          <p className="font-mono text-[11px] text-muted-foreground">{t('auth.shellFooter')}</p>
        </div>
        <div className="p-6 sm:p-10">
          <div className="mb-6 flex justify-end"><LanguageSwitcher /></div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary">{eyebrow}</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
          {children}
        </div>
      </motion.section>
    </main>
  )
}

function Field({ label, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return <label className="block text-sm font-medium">{label}<input className="mt-2 h-11 w-full rounded-lg border bg-background px-3 text-sm placeholder:text-muted-foreground" {...props} /></label>
}

function Login({ onAuthenticated }: { onAuthenticated: () => void }) {
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

function Register() {
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

function WorkspaceShell({ children, onLogout, route, title, eyebrow, userEmail }: { children: React.ReactNode; onLogout: () => void; route: Route; title: string; eyebrow: string; userEmail?: string }) {
  const { t } = useTranslation()
  const navItem = (target: Route, label: string, icon: React.ReactNode) => (
    <button
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${route === target ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-secondary hover:text-foreground'}`}
      onClick={() => navigate(target)}
      type="button"
    >
      {icon}{label}
    </button>
  )

  return <div className="min-h-screen bg-background">
    <div className="pointer-events-none fixed inset-0 surface-grid opacity-30" />
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r bg-card/85 backdrop-blur-xl lg:flex lg:flex-col">
      <div className="flex h-16 items-center gap-3 border-b px-5"><span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground"><Sparkles className="size-4" /></span><span className="font-semibold">{t('common.appName')}</span></div>
      <nav className="flex-1 space-y-1 p-3">
        <p className="px-3 py-3 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Workspace</p>
        {navItem('/profile', t('nav.profile'), <UserRound className="size-4" />)}
        {navItem('/pool', t('nav.pool'), <Library className="size-4" />)}
        {navItem('/generate', t('nav.generate'), <Wand2 className="size-4" />)}
        {navItem('/archive', t('nav.archive'), <FileText className="size-4" />)}
        {navItem('/account', t('nav.account'), <Settings className="size-4" />)}
      </nav>
      <div className="border-t p-3"><button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-secondary" onClick={onLogout} type="button"><LogOut className="size-4" />{t('nav.logout')}</button></div>
    </aside>
    <div className="relative lg:pl-64">
      <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b bg-background/80 px-5 backdrop-blur-xl sm:px-8">
        <div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{eyebrow}</p><h1 className="text-sm font-semibold">{title}</h1></div>
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <button className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm text-muted-foreground hover:bg-secondary lg:hidden" onClick={() => navigate(route === '/pool' ? '/profile' : '/pool')} type="button">
            {route === '/pool' ? <UserRound className="size-4" /> : <Library className="size-4" />}{route === '/pool' ? t('nav.profile') : t('nav.poolShort')}
          </button>
          <button className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm text-muted-foreground hover:bg-secondary lg:hidden" onClick={() => navigate('/generate')} type="button"><Wand2 className="size-4" />{t('nav.cvShort')}</button>
          <button className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm text-muted-foreground hover:bg-secondary lg:hidden" onClick={onLogout} type="button"><LogOut className="size-4" />{t('nav.logoutShort')}</button>
          <span className="hidden rounded-lg border bg-card px-3 py-2 text-sm text-muted-foreground sm:block">{userEmail}</span>
        </div>
      </header>
      {children}
    </div>
  </div>
}

function ProfilePage({ onLogout }: { onLogout: () => void }) {
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

function SourceBadge({ source }: { source: PoolSource }) {
  const { t } = useTranslation()
  const tone = source === 'manual' ? 'border-success/30 bg-success/10 text-success' : source === 'github' ? 'border-primary/30 bg-primary/10 text-primary' : 'border-warning/30 bg-warning/10 text-warning'
  return <span className={`rounded-md border px-2 py-1 font-mono text-[11px] ${tone}`}>{t(`labels.${source}`)}</span>
}

function PoolItemRow({ item, onSave, onDelete }: { item: PoolItem; onSave?: (id: string, changes: Partial<PoolItem>) => Promise<void>; onDelete?: (id: string) => Promise<void> }) {
  const { t } = useTranslation()
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState({ title: item.title ?? '', rawContent: item.raw_content, tags: item.tags.join(', '), technologies: item.technologies.join(', ') })

  function startEditing() {
    setDraft({ title: item.title ?? '', rawContent: item.raw_content, tags: item.tags.join(', '), technologies: item.technologies.join(', ') })
    setEditing(true)
  }

  async function save(event: FormEvent) {
    event.preventDefault()
    if (!onSave) return
    setBusy(true)
    try {
      await onSave(item.id, { title: draft.title.trim() || null, raw_content: draft.rawContent, tags: splitList(draft.tags), technologies: splitList(draft.technologies) })
      setEditing(false)
    } finally { setBusy(false) }
  }

  async function remove() {
    if (!onDelete || !window.confirm(t('pool.deleteConfirm'))) return
    setBusy(true)
    try { await onDelete(item.id) } finally { setBusy(false) }
  }

  return <article className="rounded-lg border bg-card/80 p-4">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <SourceBadge source={item.source} />
          <span className="rounded-md border bg-secondary px-2 py-1 text-[11px] text-muted-foreground">{t(`labels.${item.type}`)}</span>
          <span className={`rounded-md border px-2 py-1 text-[11px] ${item.verified_by_user ? 'border-success/30 bg-success/10 text-success' : 'border-warning/30 bg-warning/10 text-warning'}`}>{item.verified_by_user ? 'verified' : t('common.pending')}</span>
        </div>
        <h3 className="mt-3 truncate text-base font-semibold">{item.title || t('common.title')}</h3>
      </div>
      <div className="flex items-center gap-2">
        <span className="font-mono text-[11px] text-muted-foreground">{item.language} / vec:{item.embedding_dimensions}</span>
        {onSave && !editing && <button aria-label={t('pool.edit')} className="grid size-8 place-items-center rounded-lg border text-muted-foreground hover:bg-secondary disabled:opacity-50" disabled={busy} onClick={startEditing} title={t('pool.edit')} type="button"><Pencil className="size-3.5" /></button>}
        {onDelete && !editing && <button aria-label={t('pool.delete')} className="grid size-8 place-items-center rounded-lg border border-danger/30 text-danger hover:bg-danger/10 disabled:opacity-50" disabled={busy} onClick={() => void remove()} title={t('pool.delete')} type="button"><Trash2 className="size-3.5" /></button>}
      </div>
    </div>
    {editing ? <form className="mt-4 space-y-3" onSubmit={save}>
      <Field label={t('common.title')} onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))} value={draft.title} />
      <label className="block text-sm font-medium">{t('common.content')}<textarea className="mt-2 min-h-28 w-full rounded-lg border bg-background p-3 text-sm" onChange={(event) => setDraft((current) => ({ ...current, rawContent: event.target.value }))} required value={draft.rawContent} /></label>
      <Field label={t('pool.tags')} onChange={(event) => setDraft((current) => ({ ...current, tags: event.target.value }))} value={draft.tags} />
      <Field label={t('pool.technologies')} onChange={(event) => setDraft((current) => ({ ...current, technologies: event.target.value }))} value={draft.technologies} />
      <div className="flex gap-2">
        <button className="flex h-9 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-60" disabled={busy} type="submit">{busy ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}{t('pool.saveItem')}</button>
        <button className="h-9 rounded-lg border px-4 text-sm text-muted-foreground hover:bg-secondary" onClick={() => setEditing(false)} type="button">{t('pool.cancel')}</button>
      </div>
    </form> : <>
      <p className="mt-3 line-clamp-3 text-sm leading-6 text-muted-foreground">{item.raw_content}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {item.technologies.map((tech) => <span className="rounded-md border bg-background px-2 py-1 font-mono text-[11px] text-foreground" key={`tech-${item.id}-${tech}`}>{tech}</span>)}
        {item.tags.map((tag) => <span className="rounded-md border bg-secondary px-2 py-1 font-mono text-[11px] text-muted-foreground" key={`tag-${item.id}-${tag}`}>#{tag}</span>)}
      </div>
    </>}
  </article>
}

function PendingItem({ item, onApprove, onReject, busy }: { item: PoolItem; onApprove: (id: string) => void; onReject: (id: string) => void; busy: boolean }) {
  const { t } = useTranslation()

  return <div className="rounded-lg border bg-background/70 p-3">
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2"><SourceBadge source={item.source} /><span className="rounded-md border bg-secondary px-2 py-1 text-[11px] text-muted-foreground">{t(`labels.${item.type}`)}</span></div>
        <p className="mt-2 truncate text-sm font-medium">{item.title || t('common.title')}</p>
        <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.raw_content}</p>
      </div>
      <div className="flex shrink-0 gap-2">
        <button aria-label={t('pool.approve')} className="grid size-9 place-items-center rounded-lg border border-success/30 bg-success/10 text-success disabled:opacity-50" disabled={busy} onClick={() => onApprove(item.id)} title={t('pool.approve')} type="button"><Check className="size-4" /></button>
        <button aria-label={t('pool.reject')} className="grid size-9 place-items-center rounded-lg border border-danger/30 bg-danger/10 text-danger disabled:opacity-50" disabled={busy} onClick={() => onReject(item.id)} title={t('pool.reject')} type="button"><X className="size-4" /></button>
      </div>
    </div>
  </div>
}

function PipelineLog({ lines }: { lines: string[] }) {
  return <div className="rounded-lg border bg-background p-3 font-mono text-[11px] leading-5 text-muted-foreground">
    {lines.map((line) => <div className="flex gap-2" key={line}><span className="text-primary">&gt;</span><span>{line}</span></div>)}
  </div>
}

function PoolPage({ onLogout }: { onLogout: () => void }) {
  const { t } = useTranslation()
  const [user, setUser] = useState<User | null>(null)
  const [items, setItems] = useState<PoolItem[]>([])
  const [pendingItems, setPendingItems] = useState<PoolItem[]>([])
  const [filter, setFilter] = useState<TypeFilter>('all')
  const [form, setForm] = useState<PoolForm>(emptyPoolForm)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [uploadBusy, setUploadBusy] = useState(false)
  const [cvFile, setCvFile] = useState<File | null>(null)
  const [approvalBusyId, setApprovalBusyId] = useState<string | null>(null)
  const [githubCallback] = useState(readGithubCallback)
  const [error, setError] = useState(() => githubCallback?.status === 'error' ? t(githubCallbackErrorKey(githubCallback.reason)) : '')
  const [message, setMessage] = useState(() => githubCallback?.status === 'connected' ? t('pool.githubConnected', { username: githubCallback.username }) : '')
  const [syncLines, setSyncLines] = useState<string[]>(() => {
    const base = ['pool.graph idle', 'sources: manual pdf github', 'pending approval gate ready']
    if (githubCallback?.status === 'connected') return [`github.oauth connected ${githubCallback.username}`, 'pool.graph background job scheduled', ...base.slice(0, 1)]
    if (githubCallback?.status === 'error') return [`github.oauth failed ${githubCallback.reason ?? 'unknown'}`, ...base.slice(0, 2)]
    return base
  })

  const refresh = useCallback(async () => {
    const [me, pool, pending] = await Promise.all([api.get<User>('/me'), api.get<PoolItem[]>('/pool-items'), api.get<PoolItem[]>('/pool/pending')])
    setUser(me)
    setItems(pool)
    setPendingItems(pending)
  }, [])

  useEffect(() => {
    Promise.all([api.get<User>('/me'), api.get<PoolItem[]>('/pool-items'), api.get<PoolItem[]>('/pool/pending')])
      .then(([me, pool, pending]) => {
        setUser(me)
        setItems(pool)
        setPendingItems(pending)
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 401) onLogout()
        else setError(errorMessage(caught))
      })
      .finally(() => setLoading(false))
  }, [onLogout])

  const visibleItems = useMemo(() => filter === 'all' ? items : items.filter((item) => item.type === filter), [filter, items])
  const counts = useMemo(() => ({
    all: items.length,
    experience: items.filter((item) => item.type === 'experience').length,
    project: items.filter((item) => item.type === 'project').length,
    skill: items.filter((item) => item.type === 'skill').length,
    education: items.filter((item) => item.type === 'education').length,
  }), [items])

  function updateForm(field: keyof PoolForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function createManualItem(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setMessage('')
    try {
      const created = await api.post<PoolItem>('/pool-items', {
        type: form.type,
        title: form.title || null,
        raw_content: form.rawContent,
        tags: splitList(form.tags),
        technologies: splitList(form.technologies),
      })
      setItems((current) => [...current, created])
      setForm(emptyPoolForm)
      setMessage(t('pool.created'))
    } catch (caught) { setError(errorMessage(caught)) } finally { setBusy(false) }
  }

  async function importCv(event: FormEvent) {
    event.preventDefault()
    if (!cvFile) return
    setUploadBusy(true); setError(''); setMessage('')
    try {
      const body = new FormData()
      body.append('file', cvFile)
      const response = await api.form<PDFImportResponse>('/pool/import/pdf', body)
      setCvFile(null)
      setSyncLines((current) => [`pdf.import completed items=${response.imported_count}`, response.profile ? 'profile updated from cv' : 'profile unchanged', ...current.slice(0, 3)])
      setMessage(t('pool.cvImported', { count: response.imported_count }))
      await refresh()
    } catch (caught) { setError(errorMessage(caught)) } finally { setUploadBusy(false) }
  }

  async function approvePending(id: string) {
    setApprovalBusyId(id); setError(''); setMessage('')
    try {
      const response = await api.post<{ updated_count: number; items: PoolItem[] }>('/pool/approve', { ids: [id] })
      setPendingItems((current) => current.filter((item) => item.id !== id))
      setItems((current) => current.map((item) => response.items.find((updated) => updated.id === item.id) ?? item))
      setMessage(`${response.updated_count} ${t('pool.approved')}`)
      await refresh()
    } catch (caught) { setError(errorMessage(caught)) } finally { setApprovalBusyId(null) }
  }

  async function rejectPending(id: string) {
    setApprovalBusyId(id); setError(''); setMessage('')
    try {
      const response = await api.post<{ deleted_count: number }>('/pool/reject', { ids: [id] })
      setPendingItems((current) => current.filter((item) => item.id !== id))
      setItems((current) => current.filter((item) => item.id !== id))
      setMessage(`${response.deleted_count} ${t('pool.rejected')}`)
    } catch (caught) { setError(errorMessage(caught)) } finally { setApprovalBusyId(null) }
  }

  async function saveItem(id: string, changes: Partial<PoolItem>) {
    setError(''); setMessage('')
    try {
      const updated = await api.patch<PoolItem>(`/pool-items/${id}`, changes)
      setItems((current) => current.map((item) => item.id === id ? updated : item))
      setPendingItems((current) => current.filter((item) => item.id !== id))
      setMessage(t('pool.updated'))
    } catch (caught) { setError(errorMessage(caught)) }
  }

  async function deleteItem(id: string) {
    setError(''); setMessage('')
    try {
      await api.delete(`/pool-items/${id}`)
      setItems((current) => current.filter((item) => item.id !== id))
      setPendingItems((current) => current.filter((item) => item.id !== id))
      setMessage(t('pool.deleted'))
    } catch (caught) { setError(errorMessage(caught)) }
  }

  async function startGithubOAuth() {
    setError(''); setMessage('')
    setSyncLines((current) => ['github.oauth start requested', ...current.slice(0, 4)])
    try {
      const response = await api.post<{ authorization_url: string; state: string }>('/github/oauth/start')
      setSyncLines((current) => [`github.oauth state ${response.state.slice(0, 12)}...`, 'redirecting to github authorization', ...current.slice(0, 3)])
      window.location.href = response.authorization_url
    } catch (caught) {
      setSyncLines((current) => ['github.oauth configuration error', ...current.slice(0, 4)])
      setError(errorMessage(caught))
    }
  }

  async function queueGithubSync() {
    setError(''); setMessage('')
    setSyncLines((current) => ['github.sync queue requested', ...current.slice(0, 4)])
    try {
      const response = await api.post<{ queued: boolean }>('/github/sync')
      setSyncLines((current) => [`github.sync queued=${response.queued}`, 'pool.graph background job scheduled', ...current.slice(0, 3)])
      setMessage(t('pool.githubQueued'))
    } catch (caught) {
      setSyncLines((current) => ['github.sync queue failed', ...current.slice(0, 4)])
      setError(errorMessage(caught))
    }
  }

  return <WorkspaceShell eyebrow={t('pool.eyebrow')} onLogout={onLogout} route="/pool" title={t('pool.title')} userEmail={user?.email}>
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="flex items-start gap-4">
          <span className="grid size-11 place-items-center rounded-xl border bg-primary/10 text-primary"><Layers3 className="size-5" /></span>
          <div>
            <h2 className="text-3xl font-semibold tracking-tight">{t('pool.heading')}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{t('pool.description')}</p>
            <p className="mt-2 max-w-2xl text-xs leading-5 text-muted-foreground">{t('common.termsNote')}</p>
          </div>
        </div>
        <div className="grid grid-cols-5 gap-2 rounded-lg border bg-card/70 p-2 text-center">
          {(['all', 'experience', 'project', 'skill', 'education'] as TypeFilter[]).map((type) => (
            <button className={`min-w-20 rounded-md px-3 py-2 text-xs ${filter === type ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-secondary'}`} key={type} onClick={() => setFilter(type)} type="button">
              <span className="block font-mono">{counts[type]}</span>{type === 'all' ? t('common.all') : t(`labels.${type}`)}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="mb-5 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>}
      {message && <p className="mb-5 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">{message}</p>}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_390px]">
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card/80 px-4 py-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground"><Filter className="size-4" />{t('pool.filterLabel')} <span className="text-foreground">{filter === 'all' ? t('common.all') : t(`labels.${filter}`)}</span></div>
            <button className="flex h-9 items-center gap-2 rounded-lg border px-3 text-sm text-muted-foreground hover:bg-secondary" onClick={() => void refresh()} type="button"><RefreshCw className="size-4" />{t('common.refresh')}</button>
          </div>
          {loading ? <p className="rounded-lg border bg-card/80 p-5 text-sm text-muted-foreground">{t('pool.loading')}</p> : visibleItems.length === 0 ? <div className="rounded-lg border bg-card/80 p-8 text-center"><CircleDot className="mx-auto size-8 text-muted-foreground" /><p className="mt-3 text-sm text-muted-foreground">{t('pool.empty')}</p></div> : <div className="grid gap-3 lg:grid-cols-2">{visibleItems.map((item) => <PoolItemRow item={item} key={item.id} onDelete={deleteItem} onSave={saveItem} />)}</div>}
        </section>

        <aside className="space-y-5">
          <section className="rounded-xl border bg-card/90 p-4">
            <div className="flex items-center gap-2"><Upload className="size-4 text-primary" /><h3 className="text-sm font-semibold">{t('pool.cvUpload')}</h3></div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{t('pool.cvUploadDescription')}</p>
            <form className="mt-4 space-y-3" onSubmit={importCv}>
              <label className="flex min-h-24 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed bg-background/70 px-4 py-5 text-center text-sm text-muted-foreground hover:bg-secondary">
                <Upload className="mb-2 size-5" />
                <span>{cvFile ? t('pool.selectedFile', { name: cvFile.name }) : t('pool.choosePdf')}</span>
                <input accept="application/pdf,.pdf" className="sr-only" onChange={(event) => setCvFile(event.target.files?.[0] ?? null)} type="file" />
              </label>
              <button className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-60" disabled={uploadBusy || !cvFile} type="submit">{uploadBusy ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}{uploadBusy ? t('pool.uploadingCv') : t('pool.uploadCv')}</button>
            </form>
          </section>

          <section className="rounded-xl border bg-card/90 p-4">
            <div className="flex items-center gap-2"><Plus className="size-4 text-primary" /><h3 className="text-sm font-semibold">{t('pool.manualAdd')}</h3></div>
            <form className="mt-4 space-y-3" onSubmit={createManualItem}>
              <label className="block text-sm font-medium">{t('common.type')}<select className="mt-2 h-10 w-full rounded-lg border bg-background px-3 text-sm" onChange={(event) => updateForm('type', event.target.value as PoolType)} value={form.type}><option value="experience">{t('labels.experience')}</option><option value="project">{t('labels.project')}</option><option value="skill">{t('labels.skill')}</option><option value="education">{t('labels.education')}</option></select></label>
              <Field label={t('common.title')} onChange={(event) => updateForm('title', event.target.value)} placeholder={t('pool.itemTitlePlaceholder')} value={form.title} />
              <label className="block text-sm font-medium">{t('common.content')}<textarea className="mt-2 min-h-28 w-full rounded-lg border bg-background p-3 text-sm" onChange={(event) => updateForm('rawContent', event.target.value)} required value={form.rawContent} /></label>
              <Field label={t('pool.tags')} onChange={(event) => updateForm('tags', event.target.value)} placeholder={t('pool.tagsPlaceholder')} value={form.tags} />
              <Field label={t('pool.technologies')} onChange={(event) => updateForm('technologies', event.target.value)} placeholder={t('pool.technologiesPlaceholder')} value={form.technologies} />
              <button className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-60" disabled={busy} type="submit">{busy ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}{t('pool.addToPool')}</button>
            </form>
          </section>

          <section className="rounded-xl border bg-card/90 p-4">
            <div className="flex items-center justify-between gap-3"><div className="flex items-center gap-2"><Tags className="size-4 text-warning" /><h3 className="text-sm font-semibold">{t('pool.pendingTitle')}</h3></div><span className="font-mono text-xs text-muted-foreground">{pendingItems.length} {t('common.pending')}</span></div>
            <div className="mt-4 space-y-3">{pendingItems.length === 0 ? <p className="rounded-lg border bg-background/70 p-3 text-sm text-muted-foreground">{t('pool.pendingEmpty')}</p> : pendingItems.map((item) => <PendingItem busy={approvalBusyId === item.id} item={item} key={item.id} onApprove={approvePending} onReject={rejectPending} />)}</div>
          </section>

          <section className="rounded-xl border bg-card/90 p-4">
            <div className="flex items-center gap-2"><GitBranch className="size-4 text-primary" /><h3 className="text-sm font-semibold">{t('pool.githubSource')}</h3></div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <button className="flex h-10 items-center justify-center gap-2 rounded-lg border bg-background px-3 text-sm hover:bg-secondary" onClick={() => void startGithubOAuth()} type="button"><GitBranch className="size-4" />{t('pool.connect')}</button>
              <button className="flex h-10 items-center justify-center gap-2 rounded-lg border bg-background px-3 text-sm hover:bg-secondary" onClick={() => void queueGithubSync()} type="button"><RefreshCw className="size-4" />{t('pool.sync')}</button>
            </div>
            <div className="mt-4"><PipelineLog lines={syncLines} /></div>
          </section>
        </aside>
      </div>
    </main>
  </WorkspaceShell>
}

function ScoreShowcase({ score }: { score: number | null }) {
  const { t } = useTranslation()
  const value = Math.round(score ?? 0)
  const tone = value >= 75 ? 'text-success' : value >= 50 ? 'text-warning' : 'text-danger'
  return <section className="rounded-xl border bg-card/95 p-5 shadow-2xl shadow-black/20">
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{t('generate.atsScore')}</p>
        <p className={`mt-2 text-7xl font-semibold leading-none tracking-tight sm:text-8xl ${tone}`}>{value}</p>
      </div>
      <span className="grid size-14 place-items-center rounded-xl border bg-background text-primary"><Trophy className="size-7" /></span>
    </div>
    <div className="mt-5 h-2 overflow-hidden rounded-full bg-secondary">
      <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${value}%` }} />
    </div>
  </section>
}

function StepTimeline({ status }: { status: CVGenerationStatus | null }) {
  const { t } = useTranslation()
  const steps = status?.steps ?? (['job_parser', 'selector', 'cvtailor', 'evaluator', 'typst_renderer'] as PipelineStepName[]).map((name) => ({ name, status: 'pending' as const }))
  return <section className="rounded-xl border bg-card/90 p-4">
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2"><Play className="size-4 text-primary" /><h3 className="text-sm font-semibold">Pipeline</h3></div>
      <span className="font-mono text-xs text-muted-foreground">{status?.status ?? t('common.statusIdle')}</span>
    </div>
    <div className="mt-4 rounded-lg border bg-background p-3 font-mono text-[11px] leading-5">
      {steps.map((step) => {
        const symbol = step.status === 'completed' ? 'ok' : step.status === 'running' ? '..' : step.status === 'failed' ? '!!' : '--'
        const tone = step.status === 'completed' ? 'text-success' : step.status === 'running' ? 'text-primary' : step.status === 'failed' ? 'text-danger' : 'text-muted-foreground'
        return <div className="flex items-center gap-2" key={step.name}><span className={tone}>[{symbol}]</span><span className="text-foreground">{t(`steps.${step.name}`)}</span><span className="text-muted-foreground">{step.status}</span></div>
      })}
      {status?.generated_cv_id && <div className="mt-2 flex gap-2 text-muted-foreground"><span className="text-primary">&gt;</span><span>generated_cv_id {status.generated_cv_id.slice(0, 8)}...</span></div>}
    </div>
  </section>
}

function JobSummaryCard({ summary }: { summary: string | null }) {
  const { t } = useTranslation()

  return <section className="rounded-xl border bg-card/90 p-4">
    <div className="flex items-center gap-2"><FileText className="size-4 text-primary" /><h3 className="text-sm font-semibold">{t('generate.jobSummary')}</h3></div>
    <p className="mt-3 text-sm leading-6 text-muted-foreground">{summary || t('generate.jobSummaryPending')}</p>
  </section>
}

function ATSRecommendations({ recommendations }: { recommendations: string[] }) {
  const { t } = useTranslation()
  if (recommendations.length === 0) return null

  return <section className="rounded-xl border border-warning/30 bg-warning/10 p-4">
    <div className="flex items-center gap-2"><Sparkles className="size-4 text-warning" /><h3 className="text-sm font-semibold">{t('generate.atsRecommendations')}</h3></div>
    <ul className="mt-3 space-y-2 text-sm leading-6 text-muted-foreground">
      {recommendations.map((item) => <li className="flex gap-2" key={item}><span className="mt-2 size-1.5 shrink-0 rounded-full bg-warning" /><span>{item}</span></li>)}
    </ul>
  </section>
}

function PipelineFailure({ detail, onRetry }: { detail: string | null; onRetry: () => void }) {
  const { t } = useTranslation()

  return <div className="grid min-h-[520px] place-items-center rounded-xl border border-danger/30 bg-danger/5 p-8 text-center">
    <div>
      <TriangleAlert className="mx-auto size-10 text-danger" />
      <p className="mt-4 text-2xl font-semibold tracking-tight">{t('generate.failedTitle')}</p>
      <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">{detail || t('generate.failedUnknown')}</p>
      <button className="mt-6 h-10 rounded-lg border bg-background px-4 text-sm hover:bg-secondary" onClick={onRetry} type="button">{t('generate.failedRetry')}</button>
    </div>
  </div>
}

function BeforeAfterDiffPanel({ entries }: { entries: BeforeAfterDiff[] }) {
  const { t } = useTranslation()

  return <section className="rounded-xl border bg-card/90 p-4">
    <div className="flex items-center gap-2"><GitCompare className="size-4 text-primary" /><h3 className="text-sm font-semibold">{t('generate.beforeAfter')}</h3></div>
    {entries.length === 0 ? <p className="mt-3 text-sm text-muted-foreground">{t('generate.noDiff')}</p> : <div className="mt-4 space-y-4">
      {entries.map((entry) => <article className="rounded-lg border bg-background/70 p-3" key={entry.source_pool_item_id}>
        <p className="text-sm font-medium">{entry.title || t('generate.tailoredItem')}</p>
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{TECH_TERMS.before}</p>
            <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{entry.before}</p>
          </div>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary">{TECH_TERMS.after}</p>
            <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-foreground">{entry.after}</p>
          </div>
        </div>
      </article>)}
    </div>}
  </section>
}

function GeneratePage({ onLogout }: { onLogout: () => void }) {
  const { t } = useTranslation()
  const [user, setUser] = useState<User | null>(null)
  const [mode, setMode] = useState<JobInputMode>('text')
  const [jobText, setJobText] = useState('')
  const [jobUrl, setJobUrl] = useState('')
  const [status, setStatus] = useState<CVGenerationStatus | null>(null)
  const [selectedItems, setSelectedItems] = useState<PoolItem[]>([])
  const [pdfUrl, setPdfUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<User>('/me').then(setUser).catch((caught) => {
      if (caught instanceof ApiError && caught.status === 401) onLogout()
      else setError(errorMessage(caught))
    })
  }, [onLogout])

  useEffect(() => {
    if (!status?.pipeline_id || status.status === 'completed' || status.status === 'failed') return
    const timer = window.setInterval(() => {
      api.get<CVGenerationStatus>(`/cv-generation/${status.pipeline_id}`)
        .then(setStatus)
        .catch((caught) => setError(errorMessage(caught)))
    }, 1200)
    return () => window.clearInterval(timer)
  }, [status?.pipeline_id, status?.status])

  useEffect(() => {
    if (status?.status !== 'completed') return
    const ids = status.selected_pool_item_ids ?? []
    Promise.all(ids.map((id) => api.get<PoolItem>(`/pool-items/${id}`)))
      .then(setSelectedItems)
      .catch(() => setSelectedItems([]))
    if (!status.generated_cv_id) return
    api.blob(`/generated-cvs/${status.generated_cv_id}/download`)
      .then((blob) => {
        setPdfUrl((current) => {
          if (current) URL.revokeObjectURL(current)
          return URL.createObjectURL(blob)
        })
      })
      .catch((caught) => setError(errorMessage(caught)))
  }, [status?.status, status?.generated_cv_id, status?.selected_pool_item_ids])

  useEffect(() => () => { if (pdfUrl) URL.revokeObjectURL(pdfUrl) }, [pdfUrl])

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setStatus(null); setSelectedItems([])
    if (pdfUrl) { URL.revokeObjectURL(pdfUrl); setPdfUrl('') }
    try {
      const start = await api.post<{ pipeline_id: string }>('/cv-generation', mode === 'text' ? { raw_text: jobText } : { source_url: jobUrl })
      const firstStatus = await api.get<CVGenerationStatus>(`/cv-generation/${start.pipeline_id}`)
      setStatus(firstStatus)
    } catch (caught) { setError(errorMessage(caught)) } finally { setBusy(false) }
  }

  const done = status?.status === 'completed'
  const failed = status?.status === 'failed'

  return <WorkspaceShell eyebrow={t('generate.eyebrow')} onLogout={onLogout} route="/generate" title={t('generate.title')} userEmail={user?.email}>
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="flex items-start gap-4">
          <span className="grid size-11 place-items-center rounded-xl border bg-primary/10 text-primary"><Wand2 className="size-5" /></span>
          <div>
            <h2 className="text-3xl font-semibold tracking-tight">{t('generate.heading')}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{t('generate.description')}</p>
          </div>
        </div>
      </div>

      {error && <p className="mb-5 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>}

      <div className="grid gap-5 xl:grid-cols-[430px_minmax(0,1fr)]">
        <aside className="space-y-5">
          <section className="rounded-xl border bg-card/90 p-4">
            <div className="grid grid-cols-2 gap-2 rounded-lg border bg-background p-1">
              <button className={`flex h-10 items-center justify-center gap-2 rounded-md text-sm ${mode === 'text' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-secondary'}`} onClick={() => setMode('text')} type="button"><FileText className="size-4" />{t('generate.textMode')}</button>
              <button className={`flex h-10 items-center justify-center gap-2 rounded-md text-sm ${mode === 'url' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-secondary'}`} onClick={() => setMode('url')} type="button"><LinkIcon className="size-4" />{t('generate.urlMode')}</button>
            </div>
            <form className="mt-4 space-y-4" onSubmit={submit}>
              {mode === 'text' ? <label className="block text-sm font-medium">{t('generate.jobText')}<textarea className="mt-2 min-h-72 w-full rounded-lg border bg-background p-3 text-sm leading-6" onChange={(event) => setJobText(event.target.value)} required value={jobText} /></label> : <Field label={t('generate.jobUrl')} onChange={(event) => setJobUrl(event.target.value)} placeholder="https://..." required type="url" value={jobUrl} />}
              <button className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-60" disabled={busy || status?.status === 'running' || status?.status === 'queued'} type="submit">{busy ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}{t('generate.startPipeline')}</button>
            </form>
          </section>
          <JobSummaryCard summary={status?.job_summary ?? null} />
          <StepTimeline status={status} />
        </aside>

        <section className="space-y-5">
          {failed ? <PipelineFailure detail={status.error} onRetry={() => setStatus(null)} /> : !done ? <div className="grid min-h-[520px] place-items-center rounded-xl border bg-card/70 p-8 text-center">
            <div>
              <Sparkles className="mx-auto size-10 text-primary" />
              <p className="mt-4 text-2xl font-semibold tracking-tight">{t('generate.showcasePendingTitle')}</p>
              <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">{t('generate.showcasePendingDescription')}</p>
            </div>
          </div> : <>
            <ScoreShowcase score={status.ats_score} />
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
              <section className="space-y-3">
                <JobSummaryCard summary={status.job_summary} />
                <ATSRecommendations recommendations={status.ats_recommendations} />
                <BeforeAfterDiffPanel entries={status.before_after_diff ?? []} />
                <section className="rounded-xl border bg-card/90 p-4">
                  <div className="flex items-center justify-between gap-3"><h3 className="text-sm font-semibold">{t('generate.selectedItems')}</h3><span className="font-mono text-xs text-muted-foreground">{selectedItems.length}</span></div>
                  <div className="mt-4 grid gap-3 lg:grid-cols-2">{selectedItems.map((item) => <PoolItemRow item={item} key={item.id} />)}</div>
                </section>
              </section>
              <aside className="space-y-5">
                <section className="rounded-xl border bg-card/90 p-4">
                  <div className="flex items-center gap-2"><Eye className="size-4 text-primary" /><h3 className="text-sm font-semibold">PDF</h3></div>
                  <div className="mt-4 overflow-hidden rounded-lg border bg-background">
                    {pdfUrl ? <iframe className="h-[460px] w-full" src={pdfUrl} title={t('common.previewPdfTitle')} /> : <p className="p-4 text-sm text-muted-foreground">{t('common.preparingPdf')}</p>}
                  </div>
                  <a className={`mt-3 flex h-10 items-center justify-center gap-2 rounded-lg border bg-background px-3 text-sm hover:bg-secondary ${pdfUrl ? '' : 'pointer-events-none opacity-50'}`} download="cv-tailor.pdf" href={pdfUrl || '#'}><Download className="size-4" />{t('common.downloadPdf')}</a>
                </section>
                {status.missing_keywords.length > 0 && <section className="rounded-xl border bg-card/90 p-4">
                  <h3 className="text-sm font-semibold">{t('generate.missingKeyword')}</h3>
                  <div className="mt-3 flex flex-wrap gap-2">{status.missing_keywords.map((keyword) => <span className="rounded-md border border-warning/30 bg-warning/10 px-2 py-1 font-mono text-[11px] text-warning" key={keyword}>{keyword}</span>)}</div>
                </section>}
              </aside>
            </div>
          </>}
        </section>
      </div>
    </main>
  </WorkspaceShell>
}

function ArchivePage({ onLogout }: { onLogout: () => void }) {
  const { t } = useTranslation()
  const [user, setUser] = useState<User | null>(null)
  const [items, setItems] = useState<GeneratedCV[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    const [me, cvs] = await Promise.all([api.get<User>('/me'), api.get<GeneratedCV[]>('/generated-cvs')])
    setUser(me)
    setItems(cvs)
  }, [])

  async function download(id: string) {
    setDownloadingId(id); setError('')
    try {
      await downloadBlob(`/generated-cvs/${id}/download`, `cv-${id.slice(0, 8)}.pdf`)
    } catch (caught) { setError(errorMessage(caught)) } finally { setDownloadingId(null) }
  }

  useEffect(() => {
    Promise.all([api.get<User>('/me'), api.get<GeneratedCV[]>('/generated-cvs')])
      .then(([me, cvs]) => {
        setUser(me)
        setItems(cvs)
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 401) onLogout()
        else setError(errorMessage(caught))
      })
      .finally(() => setLoading(false))
  }, [onLogout])

  return <WorkspaceShell eyebrow={t('archive.eyebrow')} onLogout={onLogout} route="/archive" title={t('archive.title')} userEmail={user?.email}>
    <main className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex items-start gap-4">
          <span className="grid size-11 place-items-center rounded-xl border bg-primary/10 text-primary"><FileText className="size-5" /></span>
          <div>
            <h2 className="text-3xl font-semibold tracking-tight">{t('archive.heading')}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{t('archive.description')}</p>
          </div>
        </div>
        <button className="flex h-10 items-center justify-center gap-2 rounded-lg border bg-background px-3 text-sm hover:bg-secondary" onClick={() => void refresh()} type="button"><RefreshCw className="size-4" />{t('common.refresh')}</button>
      </div>
      {error && <p className="mb-5 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>}
      {loading ? <p className="rounded-lg border bg-card/80 p-5 text-sm text-muted-foreground">{t('archive.loading')}</p> : items.length === 0 ? <div className="rounded-lg border bg-card/80 p-8 text-center"><FileText className="mx-auto size-8 text-muted-foreground" /><p className="mt-3 text-sm text-muted-foreground">{t('archive.empty')}</p></div> : <section className="grid gap-3 md:grid-cols-2">
        {items.map((item) => (
          <article className="rounded-lg border bg-card/90 p-4" key={item.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-mono text-[11px] text-muted-foreground">{item.created_at ? new Date(item.created_at).toLocaleString() : item.id.slice(0, 8)}</p>
                <h3 className="mt-2 text-sm font-semibold">CV #{item.id.slice(0, 8)}</h3>
              </div>
              <span className="rounded-md border bg-secondary px-2 py-1 font-mono text-[11px] text-muted-foreground">{item.output_language}</span>
            </div>
            <div className="mt-4 flex items-center justify-between gap-3">
              <span className="text-sm text-muted-foreground">{t('generate.atsScore')}: <strong className="text-foreground">{Math.round(item.ats_score ?? 0)}</strong></span>
              <button className="flex h-9 items-center gap-2 rounded-lg border px-3 text-sm hover:bg-secondary disabled:opacity-50" disabled={!item.pdf_path || downloadingId === item.id} onClick={() => void download(item.id)} type="button">{downloadingId === item.id ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}{item.pdf_path ? t('common.downloadPdf') : t('archive.pdfPending')}</button>
            </div>
          </article>
        ))}
      </section>}
    </main>
  </WorkspaceShell>
}

const DELETE_ACCOUNT_CONFIRMATION = 'HESABIMI SIL'

function AccountPage({ onLogout }: { onLogout: () => void }) {
  const { t } = useTranslation()
  const [user, setUser] = useState<User | null>(null)
  const [notice, setNotice] = useState<KVKKNotice | null>(null)
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.get<User>('/me'), api.get<KVKKNotice>('/kvkk/aydinlatma')])
      .then(([me, kvkkNotice]) => {
        setUser(me)
        setNotice(kvkkNotice)
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 401) onLogout()
        else setError(errorMessage(caught))
      })
  }, [onLogout])

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

function App() {
  const [route, setRoute] = useState<Route>(routeFromPath)
  const [authenticated, setAuthenticated] = useState(() => Boolean(getAccessToken()))

  useEffect(() => { const sync = () => setRoute(routeFromPath()); window.addEventListener('popstate', sync); return () => window.removeEventListener('popstate', sync) }, [])
  useEffect(() => {
    const expire = () => { setAuthenticated(false); navigate('/login', true) }
    window.addEventListener(UNAUTHORIZED_EVENT, expire)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, expire)
  }, [])
  useEffect(() => {
    if (!authenticated && route !== '/login' && route !== '/register') navigate('/login', true)
    if (authenticated && (route === '/login' || route === '/register')) navigate('/profile', true)
  }, [authenticated, route])

  const logout = useCallback(() => { clearAccessToken(); setAuthenticated(false); navigate('/login', true) }, [])
  if (!authenticated && route === '/register') return <Register />
  if (!authenticated) return <Login onAuthenticated={() => { setAuthenticated(true); navigate('/profile', true) }} />
  if (route === '/pool') return <PoolPage onLogout={logout} />
  if (route === '/generate') return <GeneratePage onLogout={logout} />
  if (route === '/archive') return <ArchivePage onLogout={logout} />
  if (route === '/account') return <AccountPage onLogout={logout} />
  return <ProfilePage onLogout={logout} />
}

export default App
