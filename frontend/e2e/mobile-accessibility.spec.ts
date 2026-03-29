import { test, expect } from 'playwright/test'

test.describe('Mobile Accessibility Fixes', () => {
  // Task 2: Footer overlap + dev toolbar
  test.describe('Footer', () => {
    test('main content has sufficient bottom padding to clear footer', async ({ page }) => {
      await page.goto('/')
      const main = page.locator('main')
      const mainBox = await main.boundingBox()
      const footer = page.locator('footer')
      const footerBox = await footer.boundingBox()
      expect(mainBox).toBeTruthy()
      expect(footerBox).toBeTruthy()
      expect(mainBox!.y + mainBox!.height).toBeLessThanOrEqual(footerBox!.y + 1)
    })

    test('dev controls are hidden on mobile', async ({ page }) => {
      await page.goto('/')
      const logViewer = page.locator('button[aria-label="Log Viewer"]')
      await expect(logViewer).toBeHidden()
      const github = page.locator('a[aria-label="GitHub Repository"]')
      await expect(github).toBeVisible()
    })
  })

  // Task 3: Dark mode navigation
  test.describe('Navigation drawer', () => {
    test('mobile menu opens and nav items are visible', async ({ page }) => {
      await page.goto('/')
      const menuToggle = page.locator('button', {
        has: page.locator('.sr-only:text("Toggle menu")'),
      })
      await menuToggle.click()
      await page.waitForTimeout(300)
      const geneLink = page.locator('button:has-text("Gene Browser")')
      await expect(geneLink).toBeVisible()
      const dashboardLink = page.locator('button:has-text("Data Overview")')
      await expect(dashboardLink).toBeVisible()
    })

    test('sheet has aria-describedby', async ({ page }) => {
      await page.goto('/')
      const menuToggle = page.locator('button', {
        has: page.locator('.sr-only:text("Toggle menu")'),
      })
      await menuToggle.click()
      await page.waitForTimeout(300)
      const description = page.locator('[role="dialog"] .sr-only:text("Navigation menu")')
      await expect(description).toBeAttached()
    })
  })

  // Task 4: Network analysis form
  test.describe('Network Analysis form', () => {
    test('form fields do not overflow viewport', async ({ page }) => {
      await page.goto('/network-analysis')
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
      const clientWidth = await page.evaluate(() => document.documentElement.clientWidth)
      expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1)
    })

    test('algorithm select has aria-label', async ({ page }) => {
      await page.goto('/network-analysis')
      const select = page.locator('[aria-label="Clustering algorithm"]')
      await expect(select).toBeAttached()
    })
  })

  // Task 5: Dashboard
  test.describe('Dashboard', () => {
    test('UpSet chart does not show "Screen too narrow" message', async ({ page }) => {
      await page.goto('/dashboard?tab=overlaps')
      await page.waitForTimeout(2000)
      const narrowMessage = page.locator('text=Screen too narrow')
      await expect(narrowMessage).toBeHidden()
    })

    test('tab list does not overflow', async ({ page }) => {
      await page.goto('/dashboard')
      const tabsList = page.locator('[role="tablist"]')
      await expect(tabsList).toBeVisible()
      const isOverflowing = await tabsList.evaluate(
        (el) => el.scrollWidth > el.clientWidth + 1,
      )
      if (isOverflowing) {
        const overflow = await tabsList.evaluate((el) => getComputedStyle(el).overflowX)
        expect(['auto', 'scroll']).toContain(overflow)
      }
    })
  })

  // Task 6: Gene table columns
  test.describe('Gene Table', () => {
    test('hides HGNC ID and Sources columns on mobile', async ({ page }) => {
      await page.goto('/genes')
      await page.waitForSelector('table', { timeout: 10000 })
      const hgncHeader = page.locator('th:has-text("HGNC ID")')
      await expect(hgncHeader).toBeHidden()
      const sourcesHeader = page.locator('th:has-text("Sources")')
      await expect(sourcesHeader).toBeHidden()
      const geneHeader = page.locator('th:has-text("Gene")')
      await expect(geneHeader).toBeVisible()
    })

    test('icon buttons have aria-labels', async ({ page }) => {
      await page.goto('/genes')
      await page.waitForSelector('table', { timeout: 10000 })
      await expect(page.locator('button[aria-label="Download CSV"]')).toBeAttached()
      await expect(page.locator('button[aria-label="Clear all filters"]')).toBeAttached()
      await expect(page.locator('button[aria-label="Refresh data"]')).toBeAttached()
    })
  })

  // Task 7: Login form
  test.describe('Login form', () => {
    test('has autocomplete attributes', async ({ page }) => {
      await page.goto('/login')
      const username = page.locator('#page-login-username')
      await expect(username).toHaveAttribute('autocomplete', 'username')
      const password = page.locator('#page-login-password')
      await expect(password).toHaveAttribute('autocomplete', 'current-password')
    })

    test('password toggle has aria-label', async ({ page }) => {
      await page.goto('/login')
      const toggle = page.locator('button[aria-label="Show password"]')
      await expect(toggle).toBeAttached()
    })
  })

  // Task 8: Headings + links
  test.describe('Heading hierarchy', () => {
    test('DataSources has no heading level skip', async ({ page }) => {
      await page.goto('/data-sources')
      await page.waitForTimeout(1000)
      const headings = await page.evaluate(() => {
        const hs = document.querySelectorAll('h1, h2, h3, h4, h5, h6')
        return Array.from(hs).map((h) => ({
          level: parseInt(h.tagName.charAt(1)),
          text: h.textContent?.trim().substring(0, 50) || '',
        }))
      })
      for (let i = 1; i < headings.length; i++) {
        const gap = headings[i].level - headings[i - 1].level
        expect(
          gap,
          `Heading skip: "${headings[i - 1].text}" (h${headings[i - 1].level}) -> "${headings[i].text}" (h${headings[i].level})`,
        ).toBeLessThanOrEqual(1)
      }
    })
  })

  test.describe('About page links', () => {
    test('inline links have underline decoration', async ({ page }) => {
      await page.goto('/about')
      const geneBrowserLink = page.locator(
        'a:has-text("Gene Browser"), [href="/genes"]:has-text("Gene Browser")',
      )
      const textDecoration = await geneBrowserLink.evaluate(
        (el) => getComputedStyle(el).textDecorationLine,
      )
      expect(textDecoration).toContain('underline')
    })
  })
})
