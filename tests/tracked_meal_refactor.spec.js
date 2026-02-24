const { test, expect } = require('@playwright/test');

test('add single food to tracker and verify it is not in meals page', async ({ page }) => {
  await page.goto('/tracker');

  // Add single food to breakfast
  await page.locator('[data-testid="add-food-breakfast"]').click();
  // Select a food (Verification Beans)
  await page.locator('#addSingleFoodModal select[name="food_id"]').selectOption({ label: 'Verification Beans' });
  await page.locator('#addSingleFoodModal input[name="quantity"]').fill('200');
  await page.getByRole('button', { name: 'Add Food', exact: true }).click();

  // Verify it appears in the tracker
  // The name should be just the food name
  const mealNameLocator = page.locator('[data-testid^="meal-name-breakfast-verification-beans"]');
  await expect(mealNameLocator).toBeVisible();
  await expect(mealNameLocator).toHaveText('Verification Beans');

  // Verify it contains the food with correct quantity
  const foodRowLocator = page.locator('[data-testid^="food-row-breakfast-verification-beans"][data-testid$="verification-beans"]');
  await expect(foodRowLocator).toBeVisible();
  await expect(foodRowLocator).toContainText('Verification Beans');
  await expect(foodRowLocator).toContainText('200.0 g');

  // Navigate to Meals page
  await page.goto('/meals');

  // Verify 'Verification Beans' is NOT in the meals list as a meal name
  // It might be in the ingredients dropdown, but shouldn't be a <strong> heading in a card
  const mealCardHeading = page.locator('.card-title:has-text("Verification Beans")');
  await expect(mealCardHeading).not.toBeVisible();
});
