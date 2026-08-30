import { useTranslation } from 'react-i18next'
import { FileText, GitCompare, Play, Sparkles, TriangleAlert, Trophy } from 'lucide-react'

import { TECH_TERMS } from '@/i18n/resources'
import type { BeforeAfterDiff, CVGenerationStatus, PipelineStepName } from '@/types'

export function ScoreShowcase({ score }: { score: number | null }) {
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

export function StepTimeline({ status }: { status: CVGenerationStatus | null }) {
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

export function JobSummaryCard({ summary }: { summary: string | null }) {
  const { t } = useTranslation()

  return <section className="rounded-xl border bg-card/90 p-4">
    <div className="flex items-center gap-2"><FileText className="size-4 text-primary" /><h3 className="text-sm font-semibold">{t('generate.jobSummary')}</h3></div>
    <p className="mt-3 text-sm leading-6 text-muted-foreground">{summary || t('generate.jobSummaryPending')}</p>
  </section>
}

export function ATSRecommendations({ recommendations }: { recommendations: string[] }) {
  const { t } = useTranslation()
  if (recommendations.length === 0) return null

  return <section className="rounded-xl border border-warning/30 bg-warning/10 p-4">
    <div className="flex items-center gap-2"><Sparkles className="size-4 text-warning" /><h3 className="text-sm font-semibold">{t('generate.atsRecommendations')}</h3></div>
    <ul className="mt-3 space-y-2 text-sm leading-6 text-muted-foreground">
      {recommendations.map((item) => <li className="flex gap-2" key={item}><span className="mt-2 size-1.5 shrink-0 rounded-full bg-warning" /><span>{item}</span></li>)}
    </ul>
  </section>
}

export function PipelineFailure({ detail, onRetry }: { detail: string | null; onRetry: () => void }) {
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

export function BeforeAfterDiffPanel({ entries }: { entries: BeforeAfterDiff[] }) {
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
