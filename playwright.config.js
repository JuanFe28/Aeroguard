import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 45000,
  globalTimeout: 15 * 60 * 1000,
  expect: { timeout: 10000 },
  workers: 1,
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  outputDir: process.env.AEROGUARD_QA_OUTPUT || 'tmp/qa-app/results',
  reporter: [
    ['list'],
    ['html', { outputFolder: process.env.AEROGUARD_QA_HTML || 'tmp/qa-app/html', open: 'never' }],
    ['json', { outputFile: process.env.AEROGUARD_QA_JSON || 'tmp/qa-app/results.json' }],
  ],
  use: {
    baseURL: process.env.AEROGUARD_QA_URL || 'http://127.0.0.1:18082',
    browserName: 'chromium',
    viewport: { width: 1440, height: 1000 },
    locale: 'es-CO',
    timezoneId: 'America/Bogota',
    actionTimeout: 10000,
    navigationTimeout: 20000,
    // Las trazas pueden incluir contraseñas, JWT y cuerpos de solicitudes.
    trace: 'off',
    video: 'off',
    screenshot: 'off',
  },
});
