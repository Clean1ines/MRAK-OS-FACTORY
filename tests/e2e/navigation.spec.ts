import { test, expect } from '@playwright/test';

console.log('>>> navigation.spec.ts is loaded');
const MASTER_KEY = process.env.MASTER_KEY || '12345678';

test.describe('Project Navigation', () => {
  test('TASK-006: Clicking project in sidebar navigates to /workspace with projectId', async ({ page, request }) => {
    // 1. Login via API to get token
    const loginResp = await request.post('/api/auth/login', {
      data: { master_key: MASTER_KEY }
    });
    expect(loginResp.ok()).toBeTruthy();
    const data = await loginResp.json();
    const token = data.session_token || data.token;
    expect(token).toBeTruthy();

    // 2. Create a test project via API
    const projectName = `E2E-Project-${Date.now()}`;
    const createResp = await request.post('/api/projects', {
      headers: { 'Authorization': `Bearer ${token}` },
      data: { name: projectName, description: 'test' }
    });
    expect(createResp.status()).toBe(201);
    const project = await createResp.json();
    const projectId = project.id;

    // 3. Set token in sessionStorage for browser
    await page.addInitScript((t: string) => {
      window.sessionStorage.setItem('mrak_session_token', t);
    }, token);

    // 4. Go to main page
    await page.goto('/');
    await expect(page.locator('header')).toBeVisible();

    // 5. Locate the project in the sidebar (clickable div, not the select option)
    const projectLocator = page.locator('aside .cursor-pointer').filter({ hasText: projectName }).first();
    await expect(projectLocator).toBeVisible();
    await projectLocator.click();

    // 6. Verify URL contains ?projectId=...
    await expect(page).toHaveURL(new RegExp(`.*/workspace\\?projectId=${projectId}`), { timeout: 10000 });

    // 7. Verify the workspace sidebar shows the project name (in Current Project block)
    await expect(page.locator('aside').getByText(projectName)).toBeVisible({ timeout: 5000 });
  });
});
