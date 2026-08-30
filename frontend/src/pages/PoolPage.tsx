import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CircleDot, Filter, GitBranch, Layers3, Loader2, Plus, RefreshCw, Tags, Upload } from 'lucide-react'

import { Field } from '@/components/Field'
import { PendingItem } from '@/components/PendingItem'
import { PipelineLog } from '@/components/PipelineLog'
import { PoolItemRow } from '@/components/PoolItemRow'
import { WorkspaceShell } from '@/components/WorkspaceShell'
import { ApiError, api } from '@/lib/api'
import { errorMessage, githubCallbackErrorKey, readGithubCallback, splitList } from '@/lib/view'
import type { PDFImportResponse, PoolForm, PoolItem, PoolType, TypeFilter, User } from '@/types'

const emptyPoolForm: PoolForm = {
  type: 'experience',
  title: '',
  rawContent: '',
  tags: '',
  technologies: '',
}

export function PoolPage({ onLogout }: { onLogout: () => void }) {
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
