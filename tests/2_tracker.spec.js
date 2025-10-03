const { test, expect } = require('@playwright/test');

test('add breakfast meal', async ({ page }) => {
  await page.goto('/tracker');

  //RESET to make sure we are testing on a known state
  page.on('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: 'Reset Page' }).click();
  await expect(page.locator('#meals-breakfast').getByText('No meals tracked')).toBeVisible();


  // Add meal to breakfast
  await page.locator('[data-testid="add-meal-breakfast"]').click();
  await page.locator('select[name="meal_id"]').selectOption('3');
  await page.getByRole('button', { name: 'Add Meal', exact: true }).click();
  await expect(page.locator('[data-testid="meal-name-breakfast-protein-shake-pea-sdz-1"]')).toBeVisible();

  //edit meal
  await page.locator('[data-testid="edit-meal-breakfast-protein-shake-pea-sdz-1"]').click();
  // Use a more robust locator to find the food by its name, then target the input
  await page.locator('.d-flex.justify-content-between:has-text("Organic Strawberry Powder")').getByRole('spinbutton').fill('10');
  // "Pea Protein Concentrate" is not in the meal, so we don't need to remove it.
  await page.getByRole('button', { name: 'Save Changes' }).click();
  await expect(page.locator('[data-testid="meal-card-breakfast-protein-shake-pea-sdz-1"]')).toContainText('• Organic Strawberry Powder 10.0 g');
  await expect(page.locator('[data-testid="meal-card-breakfast-protein-shake-pea-sdz-1"]')).not.toContainText('• Pea Protein Concentrate 34.0 g');

  //add food to tracker meal
  await page.locator('[data-testid="edit-meal-breakfast-protein-shake-pea-sdz-1"]').click();
  await page.locator('#foodSelectTrackedMeal').selectOption({ label: 'Coffee' });
  await page.getByRole('button', { name: 'Add Food', exact: true }).click();
  await page.getByRole('button', { name: 'Save Changes' }).click();
  await expect(page.locator('[data-testid="meal-card-breakfast-protein-shake-pea-sdz-1"]')).toContainText('• Coffee 100.0 g');

});
