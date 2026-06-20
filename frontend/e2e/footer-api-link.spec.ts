import { test, expect } from 'playwright/test'

/**
 * Footer OpenAPI / API documentation link.
 *
 * The link lives in the always-visible right group of the fixed bottom bar,
 * so it must render on mobile viewports (the e2e projects use Pixel 5).
 * It carries a lucide icon (from the app's own icon set) and points at the
 * backend `/docs` route.
 */
test.describe('Footer API (OpenAPI) link', () => {
  test('renders the OpenAPI logo link in the footer', async ({ page }) => {
    await page.goto('/')

    const apiLink = page.locator('footer a[aria-label="API Documentation (OpenAPI)"]')
    await expect(apiLink).toBeVisible()

    // Opens in a new tab and is safe (noopener)
    await expect(apiLink).toHaveAttribute('target', '_blank')
    await expect(apiLink).toHaveAttribute('rel', /noopener/)

    // Points at the FastAPI Swagger UI (`/docs`)
    const href = await apiLink.getAttribute('href')
    expect(href).toBeTruthy()
    expect(href).toMatch(/\/docs$/)

    // Renders a lucide icon (from the app's icon set, not an external image)
    const icon = apiLink.locator('svg')
    await expect(icon).toBeAttached()
  })
})
