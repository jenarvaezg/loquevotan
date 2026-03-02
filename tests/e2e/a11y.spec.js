import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility Checks', () => {
  const routes = [
    '/',
    '/votaciones',
    '/diputados',
    '/grupos',
    '/quiz'
  ];

  for (const route of routes) {
    test(`Should not have any automatically detectable accessibility issues on ${route}`, async ({ page }) => {
      await page.goto(route);
      
      // Wait for content to load
      await page.waitForSelector('h1');
      
      const accessibilityScanResults = await new AxeBuilder({ page })
        .disableRules(['color-contrast', 'link-in-text-block', 'heading-order'])
        .analyze();
      expect(accessibilityScanResults.violations).toEqual([]);
    });
  }
});
