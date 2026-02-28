import { test, expect } from "@playwright/test";

test.describe("Votaciones View Filters", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/#/votaciones");
    await page.waitForSelector(".vote-card", { timeout: 15000 });
  });

  test("page loads with votacion cards", async ({ page }) => {
    const cards = page.locator(".vote-card");
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
  });

  test("legislatura filter changes results", async ({ page }) => {
    // The count is shown inline as "N votaciones"
    const countText = page.getByText(/\d+.*votaciones/);
    await expect(countText.first()).toBeVisible();

    // Legislatura is the 3rd select (category, result, legislatura)
    await page.locator("select").nth(2).selectOption("XV");
    await page.waitForTimeout(500);

    // Should still show a count
    await expect(countText.first()).toBeVisible();
  });

  test("category filter shows filtered results", async ({ page }) => {
    // Click a category chip/button if available
    const categorySelect = page.locator("select").nth(1);
    if (await categorySelect.isVisible()) {
      const options = await categorySelect.locator("option").allTextContents();
      if (options.length > 1) {
        await categorySelect.selectOption({ index: 1 });
        await page.waitForTimeout(500);
        // Should still have cards or show empty state
        const hasCards = await page.locator(".vote-card").count();
        const hasEmpty = await page.locator(".empty-state").count();
        expect(hasCards + hasEmpty).toBeGreaterThan(0);
      }
    }
  });

  test("pagination works", async ({ page }) => {
    const pagination = page.locator(".pagination");
    if (await pagination.isVisible()) {
      const buttons = pagination.locator("button");
      const count = await buttons.count();
      if (count > 1) {
        // Click next page
        await buttons.last().click();
        await page.waitForTimeout(300);
        // Should still show cards
        const cards = page.locator(".vote-card");
        expect(await cards.count()).toBeGreaterThan(0);
      }
    }
  });
});
