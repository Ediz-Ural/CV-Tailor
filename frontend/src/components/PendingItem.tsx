import { useTranslation } from 'react-i18next'
import { Check, X } from 'lucide-react'

import { SourceBadge } from '@/components/PoolItemRow'
import type { PoolItem } from '@/types'

export function PendingItem({ item, onApprove, onReject, busy }: { item: PoolItem; onApprove: (id: string) => void; onReject: (id: string) => void; busy: boolean }) {
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
