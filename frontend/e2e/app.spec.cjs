
const { test, expect } = require('@playwright/test');

test.describe('App Navigation and Functionality', () => {

    test('should load the dashboard / homepage', async ({ page }) => {
        // Go to root
        await page.goto('/');

        // Check url (fuzzy match)
        await expect(page).toHaveURL(/.*localhost.*/);

        // Check sidebar/navbar exists
        await expect(page.locator('.navbar')).toBeVisible();
        await expect(page.getByText('Dashboard')).toBeVisible();
    });

    test('should navigate to Advanced Simulation V2 and select engine', async ({ page }) => {
        await page.goto('/');

        // Click Navbar
        // Note: The text is "Advanced Simulation"
        await page.locator('.navbar >> text=Advanced Simulation').click();

        // Check for Engine Selector
        // Wait for it to be visible (auto-waiting in playwright)
        const engineSelect = page.locator('select').first();
        await expect(engineSelect).toBeVisible();

        // Check options
        const val = await engineSelect.inputValue();
        // Default might be 'legacy'
        expect(['legacy', 'numpy', 'numba', 'torch']).toContain(val);

        // Try selecting numpy
        await engineSelect.selectOption('numpy');
        await expect(engineSelect).toHaveValue('numpy');
    });

    test('should navigate to Walk Forward page', async ({ page }) => {
        await page.goto('/');

        // Click Navbar
        await page.locator('.navbar >> text=Walk-Forward').click();

        // Check header
        await expect(page.getByText('Walk-Forward Validation')).toBeVisible();
    });
});
