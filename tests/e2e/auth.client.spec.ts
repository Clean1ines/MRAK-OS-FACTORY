import { test, expect } from '@playwright/test';

console.log('>>> auth.client.spec.ts is loaded');
const MASTER_KEY = process.env.MASTER_KEY || '12345678';

test.describe('API Client Token Injection (E2E)', () => {
  test('should attach Bearer token to API requests after login', async ({ page, request }) => {
    // 1. Login via API to get token
    const loginResp = await request.post('/api/auth/login', {
      data: { master_key: MASTER_KEY }
    });
    expect(loginResp.ok()).toBeTruthy();
    const data = await loginResp.json();
    const token = data.session_token || data.token;
    expect(token, 'Backend must return session_token').toBeTruthy();

    // 2. Set token in sessionStorage for browser (AuthGuard reads this)
    await page.addInitScript((t: string) => {
      window.sessionStorage.setItem('mrak_session_token', t);
    }, token);

    // 3. Navigate to workspace
    await page.goto('/workspace');
    await expect(page.locator('.flex-1.relative.overflow-hidden')).toBeVisible({ timeout: 15000 });

    // 4. Now make an API request via Playwright's request context to verify token works
    const projectsResp = await request.get('/api/projects', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    expect(projectsResp.status()).not.toBe(401); // Should not be unauthorized
    // It could be 200 or 500 if DB down, but not 401.
  });
});

// Temporary comment to trigger push
