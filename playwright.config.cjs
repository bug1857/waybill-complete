const { defineConfig, devices } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests/browser',
  workers: 1, // The academic API deliberately has one solve slot.
  retries: 0,
  timeout: 45000,
  use: { baseURL: process.env.WAYBILL_BROWSER_API || 'http://127.0.0.1:10000', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
});
