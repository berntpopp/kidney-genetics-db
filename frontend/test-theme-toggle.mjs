import { chromium } from 'playwright';

(async () => {
  console.log('🧪 Testing Theme Toggle - No Deprecation Warnings\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  const warnings = [];
  const errors = [];

  // Capture console warnings and errors
  page.on('console', msg => {
    const text = msg.text();
    const type = msg.type();

    if (type === 'warning') {
      console.log('  ⚠️  WARNING:', text);
      warnings.push(text);
    } else if (type === 'error') {
      console.error('  ❌ ERROR:', text);
      errors.push(text);
    }
  });

  page.on('pageerror', error => {
    console.error('  ❌ PAGE ERROR:', error.message);
    errors.push(error.message);
  });

  try {
    console.log('1️⃣  Loading application...');
    await page.goto('http://localhost:5173/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    console.log('\n2️⃣  Checking initial theme...');
    const themeButton = page.locator('button[title*="Switch to"]').first();
    const initialTitle = await themeButton.getAttribute('title');
    console.log('    Initial theme button:', initialTitle);

    console.log('\n3️⃣  Toggling theme to dark mode...');
    await themeButton.click();
    await page.waitForTimeout(1000);

    const afterFirstToggleTitle = await themeButton.getAttribute('title');
    console.log('    After first toggle:', afterFirstToggleTitle);

    console.log('\n4️⃣  Toggling theme back to light mode...');
    await themeButton.click();
    await page.waitForTimeout(1000);

    const afterSecondToggleTitle = await themeButton.getAttribute('title');
    console.log('    After second toggle:', afterSecondToggleTitle);

    console.log('\n5️⃣  Testing mobile theme toggle...');
    // Open mobile menu
    const mobileMenuButton = page.locator('.v-app-bar-nav-icon');
    if (await mobileMenuButton.isVisible()) {
      await mobileMenuButton.click();
      await page.waitForTimeout(500);

      const mobileThemeToggle = page.locator('v-list-item').filter({ hasText: /Light Mode|Dark Mode/ }).first();
      if (await mobileThemeToggle.isVisible()) {
        await mobileThemeToggle.click();
        await page.waitForTimeout(1000);
        console.log('    Mobile theme toggle clicked');
      }
    }

    console.log('\n6️⃣  Results:');
    console.log('    Total warnings:', warnings.length);
    console.log('    Total errors:', errors.length);

    // Check for Vuetify deprecation warnings
    const deprecationWarnings = warnings.filter(w =>
      w.includes('deprecated') || w.includes('UPGRADE')
    );

    if (deprecationWarnings.length > 0) {
      console.log('\n  ⚠️  DEPRECATION WARNINGS FOUND:');
      deprecationWarnings.forEach(w => console.log('    -', w));
      console.log('\n  ❌ TEST FAILED - Deprecation warnings still present');
    } else {
      console.log('\n  ✅ TEST PASSED - No deprecation warnings!');
    }

    if (errors.length > 0) {
      console.log('\n  ❌ ERRORS FOUND:');
      errors.forEach(e => console.log('    -', e));
    }

    await page.waitForTimeout(2000);

  } catch (error) {
    console.error('\n❌ Test failed with exception:', error.message);
  } finally {
    await browser.close();
  }
})();
