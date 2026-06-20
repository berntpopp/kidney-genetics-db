import { test, expect } from 'playwright/test'

/**
 * Footer OpenAPI / API documentation link.
 *
 * The link lives in the always-visible right group of the fixed bottom bar,
 * so it must render on mobile viewports (the e2e projects use Pixel 5).
 * It carries the Swagger/OpenAPI logo and points at the backend `/docs` route.
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

    // Renders the OpenAPI logo
    const logo = apiLink.locator('img[alt="OpenAPI"]')
    await expect(logo).toBeAttached()
    await expect(logo).toHaveAttribute('src', '/swagger.png')
  })
})
