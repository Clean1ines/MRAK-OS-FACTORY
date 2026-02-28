import { test, expect } from '@playwright/test';

console.log('>>> sidebar-collapse.spec.ts is loaded');
const MASTER_KEY = process.env.MASTER_KEY || '12345678';

test.describe('Sidebar Collapse & Hamburger Menu', () => {
  test('TASK-009: Sidebar can be collapsed and reopened, home link works', async ({ page, request }) => {
    // 1. Login via API to get token
    const loginResp = await request.post('/api/auth/login', {
      data: { master_key: MASTER_KEY }
    });
    expect(loginResp.ok()).toBeTruthy();
    const data = await loginResp.json();
    const token = data.session_token || data.token;
    expect(token).toBeTruthy();

    // 2. Set token in sessionStorage
    await page.addInitScript((t: string) => {
      window.sessionStorage.setItem('mrak_session_token', t);
    }, token);

    // 3. Navigate to workspace (where hamburger with home icon exists)
    await page.goto('/workspace');
    await expect(page.locator('.flex-1.relative.overflow-hidden')).toBeVisible();

    // 4. Sidebar should be open initially (on desktop)
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();

    // 5. Find and click close button (has aria-label "Close sidebar")
    const closeButton = page.getByLabel('Close sidebar');
    await closeButton.click();

    // 6. Verify sidebar is hidden and hamburger appears
    await expect(sidebar).toBeHidden();
    const hamburger = page.getByLabel('Open sidebar');
    await expect(hamburger).toBeVisible();

    // 7. Click hamburger to reopen sidebar
    await hamburger.click();
    await expect(sidebar).toBeVisible();

    // 8. Close sidebar again, then click the home icon in hamburger menu
    await closeButton.click();
    await expect(sidebar).toBeHidden();

    const homeIcon = page.getByLabel('Go to projects');
    await expect(homeIcon).toBeVisible();
    await homeIcon.click();

    // 9. Should navigate to home page ('/')
    await expect(page).toHaveURL('/');
    await expect(page.locator('header')).toBeVisible();
  });
});
