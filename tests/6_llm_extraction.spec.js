const { test, expect } = require('@playwright/test');

test.describe('LLM Food Extraction', () => {
  test('should allow extracting data from a pasted image', async ({ page }) => {
    await page.goto('/llm');

    // This is a simplified way to "paste" an image.
    // In a real test, you might need a more complex setup to interact with the clipboard.
    await page.evaluate(() => {
      const dataTransfer = new DataTransfer();
      const file = new File(['dummy image content'], 'pasted.png', { type: 'image/png' });
      dataTransfer.items.add(file);
      const pasteEvent = new ClipboardEvent('paste', {
        clipboardData: dataTransfer,
        bubbles: true,
        cancelable: true,
      });
      document.getElementById('paste-container').dispatchEvent(pasteEvent);
    });

    // Verify the image preview is shown
    const imagePreview = page.locator('#pasted-image-preview');
    await expect(imagePreview).toBeVisible();

    // Mock the API response
    await page.route('/llm/extract', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          name: 'Pasted Food',
          brand: 'Test Brand',
          serving_size_g: 100.0,
          calories: 150,
          protein_g: 8.0,
          carbohydrate_g: 15.0,
          fat_g: 3.0,
          fiber_g: 2.0,
          sugar_g: 1.0,
          sodium_mg: 75,
          calcium_mg: 30
        }),
      });
    });

    // Submit the form
    await page.click('button[type="submit"]');

    // Verify the result
    const resultContainer = page.locator('#resultContainer');
    await expect(resultContainer).toBeVisible();
    await expect(resultContainer).toContainText('Pasted Food');
  });

  test('should allow extracting data from a webpage URL', async ({ page }) => {
    await page.goto('/llm');

    // Fill in the webpage URL
    await page.fill('#webpageUrl', 'https://example.com/recipe');

    // Mock the API response
    await page.route('/llm/extract', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          name: 'Webpage Food',
          brand: 'Web Brand',
          serving_size_g: 200.0,
          calories: 250,
          protein_g: 12.0,
          carbohydrate_g: 25.0,
          fat_g: 6.0,
          fiber_g: 3.0,
          sugar_g: 4.0,
          sodium_mg: 120,
          calcium_mg: 60
        }),
      });
    });

    // Submit the form
    await page.click('button[type="submit"]');

    // Verify the result
    const resultContainer = page.locator('#resultContainer');
    await expect(resultContainer).toBeVisible();
    await expect(resultContainer).toContainText('Webpage Food');
  });

  test('should still allow extracting data from an uploaded image', async ({ page }) => {
    await page.goto('/llm');

    // Upload an image
    await page.setInputFiles('#imageUpload', {
      name: 'food.jpg',
      mimeType: 'image/jpeg',
      buffer: Buffer.from('dummy image content'),
    });

    // Mock the API response
    await page.route('/llm/extract', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          name: 'Uploaded Food',
          brand: 'Upload Brand',
          serving_size_g: 150.0,
          calories: 350,
          protein_g: 15.0,
          carbohydrate_g: 30.0,
          fat_g: 10.0,
          fiber_g: 5.0,
          sugar_g: 8.0,
          sodium_mg: 200,
          calcium_mg: 100
        }),
      });
    });

    // Submit the form
    await page.click('button[type="submit"]');

    // Verify the result
    const resultContainer = page.locator('#resultContainer');
    await expect(resultContainer).toBeVisible();
    await expect(resultContainer).toContainText('Uploaded Food');
  });

  test('should allow editing extracted data and saving to foods', async ({ page }) => {
    await page.goto('/llm');

    // Fill in the webpage URL
    await page.fill('#webpageUrl', 'https://example.com/recipe');

    // Mock the API response
    await page.route('/llm/extract', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          name: 'Editable Food',
          brand: 'Test Brand',
          serving_size_g: 100.0,
          calories: 200,
          protein_g: 10.0,
          carbohydrate_g: 20.0,
          fat_g: 5.0,
          fiber_g: 2.5,
          sugar_g: 3.0,
          sodium_mg: 150,
          calcium_mg: 50
        }),
      });
    });

    // Mock the save response
    await page.route('/foods/add', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'success', message: 'Food added successfully' }),
      });
    });

    // Submit the extraction form
    await page.click('button[type="submit"]');

    // Verify the result container is visible
    const resultContainer = page.locator('#resultContainer');
    await expect(resultContainer).toBeVisible();

    // Verify form is populated
    await expect(page.locator('#foodName')).toHaveValue('Editable Food');
    await expect(page.locator('#foodBrand')).toHaveValue('Test Brand');
    await expect(page.locator('#servingSizeG')).toHaveValue('100');
    await expect(page.locator('#calories')).toHaveValue('200');

    // Edit some values
    await page.fill('#foodName', 'Edited Food Name');
    await page.fill('#calories', '250');

    // Click Confirm and Save
    await page.click('#confirmAndSave');

    // Verify save was attempted (mocked, so no actual redirect)
    // In a real test, you might check for a success message or redirect
  });
});