import { test, expect } from '@playwright/test'

test.describe('Home page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/#/')
    await page.waitForSelector('.stats-banner')
  })

  test('shows stats banner with counts', async ({ page }) => {
    const banner = page.locator('.stats-banner')
    await expect(banner).toBeVisible()
    // Should show diputados, votaciones, votos counts
    const statNumbers = banner.locator('.stat-number')
    await expect(statNumbers).toHaveCount(3)
  })

  test('shows top tags section', async ({ page }) => {
    const tags = page.locator('.topic-grid .topic-card')
    const count = await tags.count()
    expect(count).toBeGreaterThan(0)
  })

  test('shows latest votaciones as VoteCards', async ({ page }) => {
    const cards = page.locator('.vote-cards-grid .vote-card')
    const count = await cards.count()
    expect(count).toBeGreaterThan(0)
  })

  test('shows rebels section with deputy names', async ({ page }) => {
    const rebels = page.locator('.ranking-grid .ranking-card')
    const count = await rebels.count()
    expect(count).toBeGreaterThan(0)
    // First rebel should have a name
    await expect(rebels.first().locator('.ranking-name')).not.toBeEmpty()
  })
})
