import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test('clicking VoteCard navigates to stable ID URL', async ({ page }) => {
    await page.goto('/#/')
    await page.waitForSelector('[data-testid="vote-card"]')
    await page.getByTestId('vote-card').first().click()
    await page.waitForURL(/#\/votacion\/.+/)
    expect(page.url()).toMatch(/#\/votacion\/.+/)
  })

  test('clicking rebel navigates to diputado page', async ({ page }) => {
    await page.goto('/#/rankings')
    await page.waitForSelector('.ranking-item')
    await page.locator('.ranking-item').first().click()
    await page.waitForURL(/#\/diputado\//)
    expect(page.url()).toContain('#/diputado/')
  })

  test('HeroSearch shows dropdown and navigates', async ({ page }) => {
    await page.goto('/#/')
    const search = page.locator('.hero-search')
    await search.fill('pension')
    // Wait for dropdown to appear
    await page.waitForSelector('.autocomplete-dropdown', { timeout: 5000 })
    const dropdown = page.locator('.autocomplete-dropdown')
    await expect(dropdown).toBeVisible()
  })

  test('back link from votacion returns to votaciones', async ({ page }) => {
    await page.goto('/#/votaciones')
    await page.waitForSelector('[data-testid="vote-card"]')
    await page.getByTestId('vote-card').first().click()
    await page.waitForSelector('.back-link')
    await page.locator('.back-link').click()
    await page.waitForURL(/#\/votaciones/)
    expect(page.url()).toContain('#/votaciones')
  })
})
