/**
 * Playwright test for Backup UI functionality
 *
 * Tests:
 * 1. Login with admin credentials
 * 2. Navigate to backups page
 * 3. Load backup stats
 * 4. Create a new backup
 */

const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('1. Navigating to login page...');
    await page.goto('http://localhost:5173/login');
    await page.waitForLoadState('networkidle');

    console.log('2. Logging in with admin credentials...');
    await page.fill('input[type="text"]', 'admin');
    await page.fill('input[type="password"]', 'ChangeMe!Admin2024');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    console.log('3. Navigating to backups page...');
    await page.goto('http://localhost:5173/admin/backups');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check if stats loaded
    console.log('4. Checking if stats loaded...');
    const statsCard = await page.locator('text=Total Backups').isVisible();
    console.log('Stats card visible:', statsCard);

    // Check if backup table loaded
    console.log('5. Checking if backup table loaded...');
    const table = await page.locator('table').isVisible();
    console.log('Table visible:', table);

    // Try to create a backup
    console.log('6. Clicking Create Backup button...');
    const createButton = await page.locator('text=Create Backup').first();
    await createButton.click();
    await page.waitForTimeout(1000);

    // Check if dialog opened
    console.log('7. Checking if create dialog opened...');
    const dialog = await page.locator('text=Create Database Backup').isVisible();
    console.log('Create dialog visible:', dialog);

    // Fill in the form
    console.log('8. Filling in backup form...');
    await page.fill('textarea[placeholder*="description"]', 'Test backup from Playwright');

    console.log('9. Submitting backup creation...');
    const submitButton = await page.locator('button:has-text("Create")').last();
    await submitButton.click();

    // Wait for response
    await page.waitForTimeout(3000);

    // Check for success or error
    const hasError = await page.locator('text=error').isVisible({ timeout: 1000 }).catch(() => false);
    const hasSuccess = await page.locator('text=success').isVisible({ timeout: 1000 }).catch(() => false);

    if (hasError) {
      console.error('❌ Error detected in UI!');
      // Take screenshot
      await page.screenshot({ path: 'backup-error.png' });
    } else if (hasSuccess) {
      console.log('✅ Backup created successfully!');
    } else {
      console.log('⚠️ No clear success/error message');
      await page.screenshot({ path: 'backup-result.png' });
    }

    // Keep browser open for inspection
    console.log('\n✅ Test completed. Browser will stay open for 30 seconds for inspection...');
    await page.waitForTimeout(30000);

  } catch (error) {
    console.error('❌ Test failed with error:', error.message);
    await page.screenshot({ path: 'test-error.png' });
  } finally {
    await browser.close();
  }
})();
