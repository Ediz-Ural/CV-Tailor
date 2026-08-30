import { type FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Download, Eye, FileText, LinkIcon, Loader2, Play, Sparkles, Wand2 } from 'lucide-react'

import { Field } from '@/components/Field'
import { PoolItemRow } from '@/components/PoolItemRow'
import { WorkspaceShell } from '@/components/WorkspaceShell'
import {
  ATSRecommendations,
  BeforeAfterDiffPanel,
  JobSummaryCard,
  PipelineFailure,
  ScoreShowcase,
  StepTimeline,
} from '@/components/pipeline/ResultPanels'
import { ApiError, api } from '@/lib/api'
import { errorMessage } from '@/lib/view'
import type { CVGenerationStatus, JobInputMode, PoolItem, User } from '@/types'

export function GeneratePage({ onLogout }: { onLogout: () => void }) {
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
