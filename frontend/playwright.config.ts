import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end coverage runs against a real backend and database.
 *
 * Every outage this project has had came from the seams between the parts -
 * CORS, the /api proxy, the OAuth redirect, line endings in the entrypoint,
 * nginx resolving its upstream. Unit tests cannot see any of those, so these
 * specs drive the built frontend against a live API.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['list']] : [['list']],
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    // `vite preview` binds to localhost only, so 127.0.0.1 does not answer.
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        // `vite preview` serves the production build and keeps the /api proxy,
        // so the browser talks to the API exactly as it does in the container.
        command: 'npm run preview -- --port 4173 --strictPort',
        url: 'http://localhost:4173',
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
})
