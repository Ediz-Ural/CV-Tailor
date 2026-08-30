import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Loader2, Pencil, Trash2 } from 'lucide-react'

import { Field } from '@/components/Field'
import { splitList } from '@/lib/view'
import type { PoolItem, PoolSource } from '@/types'

export function SourceBadge({ source }: { source: PoolSource }) {
  const { t } = useTranslation()
  const tone = source === 'manual' ? 'border-success/30 bg-success/10 text-success' : source === 'github' ? 'border-primary/30 bg-primary/10 text-primary' : 'border-warning/30 bg-warning/10 text-warning'
  return <span className={`rounded-md border px-2 py-1 font-mono text-[11px] ${tone}`}>{t(`labels.${source}`)}</span>
}

export function PoolItemRow({ item, onSave, onDelete }: { item: PoolItem; onSave?: (id: string, changes: Partial<PoolItem>) => Promise<void>; onDelete?: (id: string) => Promise<void> }) {
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
