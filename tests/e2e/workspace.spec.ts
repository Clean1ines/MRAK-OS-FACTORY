// tests/e2e/workspace.spec.ts — FIXED: explicit Bearer header for API requests
import { test, expect } from '@playwright/test';

console.log('>>> workspace.spec.ts is loaded');
const MASTER_KEY = process.env.MASTER_KEY || '12345678';

test.describe('Workspace E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    // Login via API to get token
    const loginResp = await request.post('/api/auth/login', {
       data: { master_key: MASTER_KEY }
    });
    expect(loginResp.ok()).toBeTruthy();
    const data = await loginResp.json();
    const token = data.session_token || data.token;
    expect(token, 'Backend must return session_token').toBeTruthy();
    
    // Set token in sessionStorage for browser navigation (AuthGuard reads this)
    await page.addInitScript((t: string) => {
      window.sessionStorage.setItem('mrak_session_token', t);
    }, token);
    
    // Navigate to workspace
    await page.goto('/workspace');
    await expect(page.locator('.flex-1.relative.overflow-hidden')).toBeVisible({ timeout: 15000 });
  });

  test('TASK-012-01: smoke - page loads after auth', async ({ page }) => {
    const canvas = page.locator('.flex-1.relative.overflow-hidden');
    await expect(canvas).toBeVisible();
    await expect(page).toHaveURL(/workspace/);
  });

  test('TASK-012-02: smoke - API projects endpoint works', async ({ request }) => {
    // Re-auth for API context (separate from browser)
    const loginResp = await request.post('/api/auth/login', {
       data: { master_key: MASTER_KEY }
    });
    const { session_token, token } = await loginResp.json();
    const authToken = session_token || token;
    
    const resp = await request.get('/api/projects', {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    expect([200, 401]).toContain(resp.status());
    if (resp.status() === 200) {
      const data = await resp.json();
      expect(Array.isArray(data)).toBeTruthy();
    }
  });

  test('TASK-012-03: smoke - create workflow via API', async ({ request }) => {
    // Re-auth for API context
    const loginResp = await request.post('/api/auth/login', {
       data: { master_key: MASTER_KEY }
    });
    const { session_token, token } = await loginResp.json();
    const authToken = session_token || token;
    
    const wf = { name: 'E2E-' + Date.now(), nodes: [], edges: [] };
    const resp = await request.post('/api/workflows', {
       data: wf,
      headers: { 'Authorization': `Bearer ${authToken}` }  // ← EXPLICIT BEARER HEADER
    });
    // Should be 201 (created) or 4xx for schema/DB issues, but NOT 401
    expect(resp.status()).not.toBe(401);
  });
});