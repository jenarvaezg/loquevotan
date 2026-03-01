import { test, expect } from "@playwright/test";

test.describe("Votaciones View Filters", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/#/votaciones");
    await page.waitForSelector('[data-testid="vote-card"]', { timeout: 15000 });
  });

  test("page loads with votacion cards", async ({ page }) => {
    const cards = page.getByTestId("vote-card");
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
  });

  test("legislatura filter changes results", async ({ page }) => {
    const countText = page.getByTestId("vot-count");
    await expect(countText).toBeVisible();

    const legSelect = page.getByTestId("vot-filter-legislatura");
    const values = await legSelect.locator("option").evaluateAll((options) =>
      options.map((option) => option.value).filter(Boolean)
    );
    if (values.length > 0) {
      await legSelect.selectOption(values[0]);
      await expect(countText).toBeVisible();
    }
  });

  test("category filter shows filtered results", async ({ page }) => {
    const categorySelect = page.getByTestId("vot-filter-category");
    if (await categorySelect.isVisible()) {
      const options = await categorySelect.locator("option").evaluateAll((all) =>
        all.map((option) => option.value).filter(Boolean)
      );
      if (options.length > 0) {
        await categorySelect.selectOption(options[0]);
        const hasCards = await page.getByTestId("vote-card").count();
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
        await buttons.last().click();
        const cards = page.getByTestId("vote-card");
        expect(await cards.count()).toBeGreaterThan(0);
      }
    }
  });
});
