import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    extraHTTPHeaders: { 'X-Test-Run': 'playwright' },
  },
  
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Остальные браузеры можно закомментировать для ускорения локальной разработки
    // { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    // { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
  
  // WebServer config для автоматического запуска при test:e2e:ci
  webServer: {
    // Запускаем ОБА сервера через concurrently
    command: 'npm run dev',
    // Ждём готовности фронтенда (бэкенд проверяется косвенно через proxy)
    url: 'http://localhost:5173',
    // Дополнительно можно проверить бэкенд
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
    // stdout/stderr для отладки
    stdout: 'pipe',
    stderr: 'pipe',
  },
  
  // Глобальные настройки таймаутов
  expect: {
    timeout: 10000,
  },
  timeout: 30000,
});
