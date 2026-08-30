import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

const apiProxy = {
  '/api': {
    target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (requestPath: string) => requestPath.replace(/^\/api/, ''),
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    // e2e/ is driven by Playwright against a live backend, not by vitest.
    exclude: ['node_modules/**', 'dist/**', 'e2e/**'],
  },
  server: {
    port: 5173,
    proxy: apiProxy,
  },
  // `vite preview` serves the production build and needs the same proxy, which
  // is what the end-to-end suite drives.
  preview: {
    port: 4173,
    proxy: apiProxy,
  },
})
