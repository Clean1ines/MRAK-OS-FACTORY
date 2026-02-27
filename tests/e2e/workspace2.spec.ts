// tests/e2e/workspace.spec.ts — TASK-013 DEBUG MINIMAL
// Только auth + загрузка страницы + базовая проверка
// Без модальных окон, без нод, без drag-and-drop

import { test, expect } from '@playwright/test';
test.setTimeout(60000); // 60 секунд на весь тест

const MASTER_KEY = process.env.MASTER_KEY || '12345678';

test('DEBUG-001: auth + page load only', async ({ page, request }) => {
  console.log('[DEBUG] Step 1: Posting to /api/auth/login...');
  
  // FIXED: correct Playwright API request syntax
  const loginResp = await request.post('/api/auth/login', {
    data: { master_key: MASTER_KEY }  // ← data: обязательно
  });
  
  console.log(`[DEBUG] Login response status: ${loginResp.status()}`);
  expect(loginResp.ok(), `Login failed: ${await loginResp.text()}`).toBeTruthy();
  
  const responseData = await loginResp.json();
  console.log(`[DEBUG] Login response body keys: ${Object.keys(responseData).join(', ')}`);
  
  const token = responseData.session_token || responseData.token;
  expect(token, 'No token in response').toBeTruthy();
  console.log(`[DEBUG] Token received (first 10 chars): ${token.substring(0, 10)}...`);
  
  // Inject token into sessionStorage BEFORE page load
  console.log('[DEBUG] Step 2: Injecting token into sessionStorage...');
  await page.addInitScript((t: string) => {
    console.log('[PAGE] initScript: setting mrak_session_token');
    window.sessionStorage.setItem('mrak_session_token', t);
  }, token);
  
  // Navigate to workspace
  console.log('[DEBUG] Step 3: Navigating to /workspace...');
  const gotoStart = Date.now();
  
  await page.goto('/workspace', { waitUntil: 'domcontentloaded', timeout: 30000 });
  
  console.log(`[DEBUG] Page loaded in ${Date.now() - gotoStart}ms. URL: ${page.url()}`);
  
  // Basic visibility checks
  console.log('[DEBUG] Step 4: Checking canvas visibility...');
  const canvas = page.locator('.flex-1.relative.overflow-hidden');
  
  const canvasVisible = await canvas.isVisible({ timeout: 10000 }).catch(() => false);
  console.log(`[DEBUG] Canvas visible: ${canvasVisible}`);
  
  if (canvasVisible) {
    console.log('[DEBUG] ✓ Test passed: auth + page load successful');
  } else {
    console.log('[DEBUG] ✗ Canvas not visible — taking screenshot...');
    await page.screenshot({ path: 'test-results/debug-page-load.png', fullPage: true });
    console.log('[DEBUG] Screenshot saved: test-results/debug-page-load.png');
  }
  
  expect(canvasVisible, 'Canvas should be visible after auth').toBeTruthy();
});
