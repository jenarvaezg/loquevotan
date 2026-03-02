import { test, expect } from '@playwright/test'

test.describe('Home page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('[data-testid="home-stats"]')
  })

  test('shows stats banner with counts', async ({ page }) => {
    const banner = page.getByTestId('home-stats')
    await expect(banner).toBeVisible()
    const statNumbers = banner.locator('.stat-number')
    await expect(statNumbers).toHaveCount(3)
  })

  test('shows top tags section', async ({ page }) => {
    const tags = page.getByTestId('home-top-tags').locator('.topic-card')
    const count = await tags.count()
    expect(count).toBeGreaterThan(0)
  })

  test('shows latest votaciones as VoteCards', async ({ page }) => {
    const cards = page.getByTestId('home-latest-votes').getByTestId('vote-card')
    const count = await cards.count()
    expect(count).toBeGreaterThan(0)
  })

  test('shows quiz banner', async ({ page }) => {
    const quizBanner = page.getByTestId('home-quiz-banner')
    await expect(quizBanner).toBeVisible()
    await expect(quizBanner.getByRole('heading')).toContainText('¿Con quién coincide más tu voto?')
  })
})
