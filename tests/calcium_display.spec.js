const { test, expect } = require('@playwright/test');

test('should display Calcium in Daily Totals section', async ({ page }) => {
  // Navigate to tracker page
  await page.goto('/tracker');

  // Check for Daily Totals card
  const dailyTotalsCard = page.locator('.card:has-text("Daily Totals")');
  await expect(dailyTotalsCard).toBeVisible();

  // Check for Calcium label and value using test-id
  const calciumValue = page.getByTestId('daily-calcium-value');
  await expect(calciumValue).toBeVisible();
  await expect(calciumValue).toContainText(/^[0-9]+mg$/);
});
