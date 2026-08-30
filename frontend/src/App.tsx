import { useCallback, useEffect, useState } from 'react'

import { AccountPage } from '@/pages/AccountPage'
import { ArchivePage } from '@/pages/ArchivePage'
import { GeneratePage } from '@/pages/GeneratePage'
import { Login } from '@/pages/Login'
import { PoolPage } from '@/pages/PoolPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { Register } from '@/pages/Register'
import { UNAUTHORIZED_EVENT } from '@/lib/api'
import { clearAccessToken, getAccessToken } from '@/lib/auth'
import { navigate, routeFromPath } from '@/lib/routing'
import type { Route } from '@/types'

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
