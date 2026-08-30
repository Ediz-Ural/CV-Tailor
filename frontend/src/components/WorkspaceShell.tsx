import { useTranslation } from 'react-i18next'
import { FileText, Library, LogOut, Settings, Sparkles, UserRound, Wand2 } from 'lucide-react'

import { LanguageSwitcher } from '@/components/LanguageSwitcher'
import { navigate } from '@/lib/routing'
import type { Route } from '@/types'

export function WorkspaceShell({ children, onLogout, route, title, eyebrow, userEmail }: { children: React.ReactNode; onLogout: () => void; route: Route; title: string; eyebrow: string; userEmail?: string }) {
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
