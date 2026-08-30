import type { Route } from '@/types'

export function routeFromPath(): Route {
  if (window.location.pathname === '/register') return '/register'
  if (window.location.pathname === '/profile') return '/profile'
  if (window.location.pathname === '/pool') return '/pool'
  if (window.location.pathname === '/generate') return '/generate'
  if (window.location.pathname === '/archive') return '/archive'
  if (window.location.pathname === '/account') return '/account'
  return '/login'
}

export function navigate(path: Route, replace = false) {
  window.history[replace ? 'replaceState' : 'pushState']({}, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}
