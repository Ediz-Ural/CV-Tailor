import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Download, FileText, Loader2, RefreshCw } from 'lucide-react'

import { WorkspaceShell } from '@/components/WorkspaceShell'
import { ApiError, api } from '@/lib/api'
import { downloadBlob, errorMessage, jobLabel } from '@/lib/view'
import type { GeneratedCV, Job, User } from '@/types'

export function ArchivePage({ onLogout }: { onLogout: () => void }) {
  const { t } = useTranslation()
  const [user, setUser] = useState<User | null>(null)
  const [items, setItems] = useState<GeneratedCV[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    const [me, cvs, jobList] = await Promise.all([api.get<User>('/me'), api.get<GeneratedCV[]>('/generated-cvs'), api.get<Job[]>('/jobs')])
    setUser(me)
    setItems(cvs)
    setJobs(jobList)
  }, [])

  // Without this the archive is a list of opaque ids: nothing says which posting
  // each CV was written for.
  const jobLabels = useMemo(() => new Map(jobs.map((job) => [job.id, jobLabel(job)])), [jobs])

  async function download(id: string) {
    setDownloadingId(id); setError('')
    try {
      await downloadBlob(`/generated-cvs/${id}/download`, `cv-${id.slice(0, 8)}.pdf`)
    } catch (caught) { setError(errorMessage(caught)) } finally { setDownloadingId(null) }
  }

  useEffect(() => {
    Promise.all([api.get<User>('/me'), api.get<GeneratedCV[]>('/generated-cvs'), api.get<Job[]>('/jobs')])
      .then(([me, cvs, jobList]) => {
        setUser(me)
        setItems(cvs)
        setJobs(jobList)
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
                <h3 className="mt-2 text-sm font-semibold">{jobLabels.get(item.job_id) ?? t('archive.jobUnknown')}</h3>
                <p className="mt-1 font-mono text-[11px] text-muted-foreground">CV #{item.id.slice(0, 8)}</p>
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
