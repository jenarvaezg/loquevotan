import { test, expect } from '@playwright/test'

test.describe('Votacion Detail', () => {
  test('loads votacion by stable ID', async ({ page }) => {
    await page.goto('/votacion/XV-164-1')
    // Wait for the detail to render
    await page.waitForSelector('.detail-header')
    const title = page.locator('.detail-header h1')
    await expect(title).not.toBeEmpty()
  })

  test('shows result badge and vote bar', async ({ page }) => {
    await page.goto('/votacion/XV-164-1')
    await page.waitForSelector('.detail-header')
    // Result badge (Aprobada/Rechazada)
    await expect(page.locator('.result-badge').first()).toBeVisible()
    // Vote bar
    await expect(page.locator('.vote-bar').first()).toBeVisible()
  })

  test('shows vote totals', async ({ page }) => {
    await page.goto('/votacion/XV-164-1')
    await page.waitForSelector('.vote-totals')
    const totals = page.locator('.vote-total-item')
    await expect(totals).toHaveCount(4) // favor, contra, abstencion, total
  })

  test('URL has stable ID format', async ({ page }) => {
    await page.goto('/votacion/XV-164-1')
    await page.waitForSelector('.detail-header')
    expect(page.url()).toMatch(/\/votacion\/[A-Z]+-\d+-\d+/)
  })

  test('group breakdown table loads', async ({ page }) => {
    await page.goto('/votacion/XV-164-1')
    // Wait for votos to load (async tier 3)
    await page.waitForSelector('table tbody tr', { timeout: 15000 })
    const rows = page.locator('table').first().locator('tbody tr')
    const count = await rows.count()
    expect(count).toBeGreaterThan(0)
  })
})
