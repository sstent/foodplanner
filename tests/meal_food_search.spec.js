const { test, expect } = require('@playwright/test');

test.describe('Meal and Food Search & Sorting', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/tracker');
    // Ensure we're in a known state
    page.on('dialog', dialog => dialog.accept());
    const resetBtn = page.getByRole('button', { name: 'Reset Page' });
    if (await resetBtn.isVisible()) {
      await resetBtn.click();
    }
  });

  test('Add Meal modal should be sorted alphabetically and searchable', async ({ page }) => {
    // Open Add Meal modal for Breakfast
    await page.locator('[data-testid="add-meal-breakfast"]').click();
    
    // Check for search input
    const searchInput = page.locator('[data-testid="meal-search-input"]');
    await expect(searchInput).toBeVisible();

    // Check alphabetical sorting
    const mealOptions = page.locator('[data-testid="meal-option"]');
    const count = await mealOptions.count();
    let prevText = "";
    for (let i = 0; i < count; i++) {
      const text = await mealOptions.nth(i).innerText();
      if (text.trim() === "" || text.includes("Choose meal...")) continue;
      
      if (prevText !== "") {
        console.log(`Comparing: "${prevText}" to "${text}"`);
        const cmp = text.localeCompare(prevText, 'en', { sensitivity: 'base' });
        if (cmp < 0) {
            console.error(`Sort order failure: "${prevText}" should come after "${text}" (cmp: ${cmp})`);
        }
        expect(cmp).toBeGreaterThanOrEqual(0);
      }
      prevText = text;
    }

    // Test real-time filtering
    await searchInput.fill('Protein');
    const filteredOptions = page.locator('[data-testid="meal-option"]:visible');
    const filteredCount = await filteredOptions.count();
    for (let i = 0; i < filteredCount; i++) {
      const text = await filteredOptions.nth(i).innerText();
      expect(text.toLowerCase()).toContain('protein');
    }
  });

  test('Add Food modal should be sorted alphabetically and searchable', async ({ page }) => {
    // Open Add Food modal for Breakfast
    await page.locator('[data-testid="add-food-breakfast"]').click();

    // Check for search input
    const searchInput = page.locator('[data-testid="food-search-input"]');
    await expect(searchInput).toBeVisible();

    // Check alphabetical sorting
    const foodOptions = page.locator('[data-testid="food-option"]');
    const count = await foodOptions.count();
    let prevText = "";
    for (let i = 0; i < count; i++) {
      const text = await foodOptions.nth(i).innerText();
      if (text.trim() === "" || text.includes("Choose food...")) continue;

      if (prevText !== "") {
        console.log(`Comparing: "${prevText}" to "${text}"`);
        const cmp = text.localeCompare(prevText, 'en', { sensitivity: 'base' });
        if (cmp < 0) {
            console.error(`Sort order failure: "${prevText}" should come after "${text}" (cmp: ${cmp})`);
        }
        expect(cmp).toBeGreaterThanOrEqual(0);
      }
      prevText = text;
    }

    // Test real-time filtering
    await searchInput.fill('Organic');
    const filteredOptions = page.locator('[data-testid="food-option"]:visible');
    const filteredCount = await filteredOptions.count();
    for (let i = 0; i < filteredCount; i++) {
      const text = (await filteredOptions.nth(i).innerText()).toLowerCase();
      const brand = (await filteredOptions.nth(i).getAttribute('data-brand') || "").toLowerCase();
      expect(text.includes('organic') || brand.includes('organic')).toBeTruthy();
    }
  });
});
