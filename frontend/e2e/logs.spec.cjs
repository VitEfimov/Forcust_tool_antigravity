
const { test, expect } = require('@playwright/test');

test.describe('Live Logs Feature', () => {
    test('should open log drawer and display logs', async ({ page }) => {
        // 1. Go to Walk Forward
        await page.goto('/');
        await page.locator('.navbar >> text=Walk-Forward').click();

        // 2. Click "Show Live Logs" button
        // It is in the config panel, small button
        await page.click('text=Show Live Logs');

        // 3. Verify Drawer Visible
        const drawer = page.locator('text=Live Server Logs');
        await expect(drawer).toBeVisible();

        // 4. Check for logic (Polling)
        // The logs might be empty initially "Waiting for logs..."
        await expect(page.locator('text=Waiting for logs...').or(page.locator('text=Fetching'))).toBeVisible();

        // 5. Close Drawer
        await page.click('text=Close');
        await expect(drawer).not.toBeVisible();
    });
});
