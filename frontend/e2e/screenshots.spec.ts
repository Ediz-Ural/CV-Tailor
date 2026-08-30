import { expect, test } from '@playwright/test'

/**
 * Captures the README screenshots from a real, running stack.
 *
 * Not part of the normal suite - it needs a seeded account and a live provider
 * key. Run it explicitly:
 *   SHOTS_EMAIL=... npx playwright test e2e/screenshots.spec.ts
 */

const email = process.env.SHOTS_EMAIL
const password = process.env.SHOTS_PASSWORD ?? 'strong-password'
const outDir = process.env.SHOTS_DIR ?? 'docs/screenshots'

test.skip(!email, 'set SHOTS_EMAIL to capture screenshots')
test.describe.configure({ mode: 'serial' })

test.use({ viewport: { width: 1440, height: 900 } })

test('capture the workspace screens', async ({ page }) => {
  test.setTimeout(300_000)

  await page.goto('/login')
  await page.getByLabel(/e-?posta|email/i).fill(email as string)
  await page.getByLabel(/parola|password/i).fill(password)
  // The shell fades in, so a shot taken right after the fill catches a frame
  // that is still almost black.
  await page.waitForTimeout(1_500)
  await page.screenshot({ path: `${outDir}/01-login.png` })
  await page.getByRole('button', { name: /giri[şs] yap|sign in|log in/i }).click()
  await expect(page).toHaveURL(/\/profile$/)

  await page.goto('/pool')
  await expect(page.locator('article').first()).toBeVisible()
  await page.screenshot({ path: `${outDir}/02-pool.png`, fullPage: true })

  await page.goto('/generate')
  await page.getByLabel(/[İi]lan metni|job text/i).fill(
    'Senior Backend Engineer. We are looking for an engineer with strong Python and ' +
      'FastAPI experience building REST APIs at scale. You will work with PostgreSQL, ' +
      'Redis and Docker, and deploy to Kubernetes. Nice to have: Kafka, Terraform, AWS.',
  )
  await page.getByRole('button', { name: /ba[şs]lat|start/i }).click()

  // The pipeline panel mid-run is the screenshot that shows how the tool works.
  await page.waitForTimeout(4_000)
  await page.screenshot({ path: `${outDir}/03-pipeline-running.png` })

  // Waiting for the text "ATS" matches the placeholder panel too, which says the
  // score will appear once the pipeline finishes - so the shot used to be taken
  // mid-run. The download button exists only after the PDF is rendered.
  await expect(page.getByRole('link', { name: /PDF indir|Download PDF/i })).toBeVisible({ timeout: 240_000 })
  await page.waitForTimeout(6_000)
  await page.screenshot({ path: `${outDir}/04-result.png`, fullPage: true })

  await page.goto('/archive')
  await expect(page.locator('article').first()).toBeVisible({ timeout: 30_000 })
  await page.screenshot({ path: `${outDir}/05-archive.png`, fullPage: true })

  await page.goto('/account')
  await expect(page.getByText(/KVKK/i).first()).toBeVisible({ timeout: 30_000 })
  await page.screenshot({ path: `${outDir}/06-account.png`, fullPage: true })
})
