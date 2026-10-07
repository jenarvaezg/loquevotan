import { test, expect } from '@playwright/test'

test.describe('Home page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('[data-testid="home-manifest-loaded"]')
  })

  test('draws the featured vote as the chamber and asks its question', async ({ page }) => {
    const spotlight = page.getByTestId('home-spotlight')
    const seats = spotlight.locator('.hemicycle-seat')
    await expect(seats.first()).toBeVisible()
    expect(await seats.count()).toBeGreaterThan(100)
    await expect(spotlight.getByRole('heading', { level: 2 })).toHaveText(/^¿.+\?$/)
  })

  test('switches the featured vote from the picker', async ({ page }) => {
    const heading = page.getByTestId('home-spotlight').getByRole('heading', { level: 2 })
    const first = await heading.textContent()
    const picker = page.getByTestId('home-featured-votes').getByRole('button')
    await picker.nth(1).click()
    await expect(picker.nth(1)).toHaveAttribute('aria-pressed', 'true')
    await expect(heading).not.toHaveText(first)
  })

  test('answers the party question and follows the chosen party', async ({ page }) => {
    const ask = page.getByTestId('home-ask-party')
    await expect(ask.getByTestId('ask-answer')).toHaveText(/^\d+ de \d+$/)
    await ask.getByTestId('ask-party-select').selectOption('PSOE')
    await expect(ask.getByRole('button', { name: 'PSOE', exact: true })).toHaveAttribute('aria-pressed', 'true')
  })

  test('lists latest votes linking to their page', async ({ page }) => {
    const rows = page.getByTestId('home-latest-votes').getByTestId('home-vote-row')
    expect(await rows.count()).toBeGreaterThan(0)
    await expect(rows.first()).toHaveAttribute('href', /\/votacion\/.+/)
  })

  test('shows quiz banner', async ({ page }) => {
    const quizBanner = page.getByTestId('home-quiz-banner')
    await expect(quizBanner).toBeVisible()
    await expect(quizBanner.getByRole('heading')).toContainText('¿Y tú, qué habrías votado?')
  })

  test('does not expose reliability copy on the public home', async ({ page }) => {
    await expect(page.locator('body')).not.toContainText(/Fiabilidad con avisos|Fiabilidad estable|Fiabilidad con incidencias/)
  })
})
