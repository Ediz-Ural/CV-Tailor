import { expect, test, type Page } from '@playwright/test'

/**
 * These run against a real API and database.
 *
 * They deliberately stay on flows that do not call an LLM provider, so the
 * suite never needs a paid key: registration, auth, profile, the pool CRUD and
 * the guard that refuses generation until the user has stored their own key.
 */

function uniqueEmail(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10_000)}@example.test`
}

const PASSWORD = 'strong-password'

async function register(page: Page, email: string) {
  await page.goto('/register')
  await page.getByLabel(/e-?posta|email/i).fill(email)
  await page.getByLabel(/parola|password/i).fill(PASSWORD)
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: /kayit ol|register/i }).click()
  await expect(page).toHaveURL(/\/login$/)
}

async function login(page: Page, email: string) {
  await page.goto('/login')
  await page.getByLabel(/e-?posta|email/i).fill(email)
  await page.getByLabel(/parola|password/i).fill(PASSWORD)
  await page.getByRole('button', { name: /giris yap|sign in|log in/i }).click()
  await expect(page).toHaveURL(/\/profile$/)
}

test('a new account can register, sign in and land in the workspace', async ({ page }) => {
  const email = uniqueEmail('signup')

  await register(page, email)
  await login(page, email)

  // Reaching the workspace at all proves the browser could call the API:
  // the origin is allowed and the /api proxy resolves.
  await expect(page.getByRole('heading', { level: 2 })).toBeVisible()
  await expect(page.getByText(email)).toBeVisible()
})

test('registration is refused without KVKK consent', async ({ page }) => {
  await page.goto('/register')
  await page.getByLabel(/e-?posta|email/i).fill(uniqueEmail('noconsent'))
  await page.getByLabel(/parola|password/i).fill(PASSWORD)

  // The submit button stays disabled until consent is given.
  await expect(page.getByRole('button', { name: /kayit ol|register/i })).toBeDisabled()
})

test('a profile survives a reload', async ({ page }) => {
  const email = uniqueEmail('profile')
  await register(page, email)
  await login(page, email)

  await page.getByLabel(/ad soyad|full name/i).fill('Ada Lovelace')
  await page.getByRole('button', { name: /olustur|kaydet|create|save/i }).click()
  await expect(page.getByText(/kaydedildi|saved/i)).toBeVisible()

  await page.reload()
  await expect(page.getByLabel(/ad soyad|full name/i)).toHaveValue('Ada Lovelace')
})

test('a pool item can be added, edited and deleted', async ({ page }) => {
  const email = uniqueEmail('pool')
  await register(page, email)
  await login(page, email)
  await page.goto('/pool')

  await page.getByLabel(/^icerik|^content/i).fill('Built REST API services with FastAPI.')
  await page.getByLabel(/^baslik|^title/i).first().fill('Backend Platform')
  await page.getByRole('button', { name: /havuza ekle|add to pool/i }).click()

  const card = page.locator('article').filter({ hasText: 'Backend Platform' })
  await expect(card).toBeVisible({ timeout: 20_000 })

  await card.getByRole('button', { name: /duzenle|edit/i }).click()
  await card.getByLabel(/^baslik|^title/i).fill('Backend Platform v2')
  await card.getByRole('button', { name: /^kaydet$|^save$/i }).click()
  await expect(page.locator('article').filter({ hasText: 'Backend Platform v2' })).toBeVisible()

  page.once('dialog', (dialog) => dialog.accept())
  await page
    .locator('article')
    .filter({ hasText: 'Backend Platform v2' })
    .getByRole('button', { name: /^sil$|^delete$/i })
    .click()
  await expect(page.locator('article').filter({ hasText: 'Backend Platform v2' })).toHaveCount(0)
})

test('generation is refused until the user stores their own API key', async ({ page }) => {
  const email = uniqueEmail('nokey')
  await register(page, email)
  await login(page, email)

  await page.goto('/account')
  await expect(page.getByText(/anahtar eklemedin|no key added yet/i)).toBeVisible()

  await page.goto('/generate')
  await page.getByLabel(/ilan metni|job text/i).fill('We need a backend engineer with FastAPI experience.')
  await page.getByRole('button', { name: /baslat|start/i }).click()

  // The server key must never be spent on a user who has not brought their own.
  await expect(page.getByText(/anahtar/i).first()).toBeVisible()
})

test('the interface can switch between Turkish and English', async ({ page }) => {
  await page.goto('/login')

  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await expect(page.getByRole('button', { name: /sign in|log in/i })).toBeVisible()

  await page.getByRole('button', { name: 'TR', exact: true }).click()
  await expect(page.getByRole('button', { name: /giris yap/i })).toBeVisible()
})
