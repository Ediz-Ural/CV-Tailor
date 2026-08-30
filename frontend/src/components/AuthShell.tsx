import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { Sparkles } from 'lucide-react'

import { LanguageSwitcher } from '@/components/LanguageSwitcher'

export function AuthShell({ children, eyebrow, title, description }: { children: React.ReactNode; eyebrow: string; title: string; description: string }) {
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
