const { test, expect } = require('@playwright/test');

test.describe('Open Food Facts Integration', () => {
  test('should allow adding a food from Open Food Facts', async ({ page }) => {
    await page.goto('/foods');

    // 1. Click the "Add from Open Food Facts" button
    await page.click('button[data-testid="add-from-open-food-facts"]');

    // 2. The modal should be visible
    const modal = page.locator('#addFromOpenFoodFactsModal');
    await expect(modal).toBeVisible();

    // 3. Search for a food
    const searchInput = modal.locator('input[name="openfoodfacts_query"]');
    const searchButton = modal.locator('button:has-text("Search")');

    // Fill the search input
    await searchInput.fill('Nutella');

    // Wait for the API response after clicking the search button
    const [response] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/foods/search_openfoodfacts') && resp.status() === 200),
      searchButton.click()
    ]);

    // 4. Wait for search results and select the first one
    const resultsContainer = modal.locator('#openFoodFactsResults');
    const firstResult = resultsContainer.locator('.list-group-item').first();
    await expect(firstResult).toBeVisible({ timeout: 10000 });
    await firstResult.click();

    // 5. Verify that the form is populated with the selected food's data
    await expect(modal.locator('input[name="name"]')).not.toHaveValue('');
    await expect(modal.locator('input[name="brand"]')).not.toHaveValue('');
    await expect(modal.locator('input[name="calories"]')).not.toHaveValue('0');

    // 6. Submit the form to add the food
    const addFoodButton = modal.locator('button:has-text("Add Food")');
    await addFoodButton.click();

    // 7. Wait for the modal to disappear and the page to reload
    await expect(modal).not.toBeVisible(); // Wait for modal to hide
    await page.waitForLoadState('networkidle'); // Wait for page reload

    // 8. Verify the food is added to the table
    const newFoodRow = page.locator('tr').filter({ hasText: /Nutella/i });
    await expect(newFoodRow).toBeVisible();
  });
});