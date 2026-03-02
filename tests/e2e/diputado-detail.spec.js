import { test, expect } from '@playwright/test'

test.describe('Diputado Detail', () => {
  // Use a known rebel from manifest
  const deputyName = 'Salvador Armendáriz, Carlos Casimiro'
  const encodedName = encodeURIComponent(deputyName)

  test('loads deputy profile', async ({ page }) => {
    await page.goto(`/diputado/${encodedName}`)
    await page.waitForSelector('.detail-header')
    const h1 = page.locator('.detail-header h1')
    await expect(h1).toContainText('Salvador')
  })

  test('shows stat cards', async ({ page }) => {
    await page.goto(`/diputado/${encodedName}`)
    await page.waitForSelector('.stat-cards')
    const cards = page.locator('.stat-card')
    await expect(cards).toHaveCount(4) // total, favor, contra, abstencion
  })

  test('shows vote bar', async ({ page }) => {
    await page.goto(`/diputado/${encodedName}`)
    await page.waitForSelector('.vote-bar')
    await expect(page.locator('.vote-bar').first()).toBeVisible()
  })

  test('history table loads with votacion links using stable IDs', async ({ page }) => {
    await page.goto(`/diputado/${encodedName}`)
    // Wait for vote history to load
    await page.waitForSelector('.responsive-table tbody tr', { timeout: 15000 })
    // Check a link in the history table points to a stable ID
    const firstLink = page.locator('.responsive-table tbody tr').first().locator('a[href*="/votacion/"]')
    const href = await firstLink.getAttribute('href')
    expect(href).toMatch(/\/votacion\/[A-Z]+-\d+-\d+/)
  })
})
