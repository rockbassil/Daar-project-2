// Optional development check. Install: npm install --prefix .tmp-browser playwright-core
// Requires the app on port 8000 and Chrome or Edge installed locally.
const { chromium } = require('../.tmp-browser/node_modules/playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const errors = [];
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  const output = path.join(__dirname, '..', 'reports', 'results');
  fs.mkdirSync(output, { recursive: true });
  try {
    await page.goto('http://127.0.0.1:8000/');
    await page.waitForFunction(() => document.querySelector('#collection-strip').textContent.includes('books to explore'));
    await page.screenshot({ path: path.join(output, 'desktop-home.png'), fullPage: true });
    await page.locator('#query').fill('whale');
    await page.getByRole('button', { name: 'Explore books' }).click();
    await page.waitForFunction(() => document.querySelectorAll('.book-card').length > 0);
    assert.match(await page.locator('#results').innerText(), /Moby Dick/);
    assert.ok(await page.locator('.recommendation').count() > 0, 'Expected recommendations for whale.');
    await page.locator('#ranking').selectOption('frequency');
    await page.waitForFunction(() => document.querySelector('.book-card h3')?.textContent.includes('Moby Dick'));
    await page.getByText('Advanced / Regex', { exact: true }).click();
    await page.locator('#query').fill('sea|ocean');
    await page.getByRole('button', { name: 'Explore books' }).click();
    await page.waitForFunction(() => !document.querySelector('#matched-terms').hidden);
    assert.match(await page.locator('#matched-terms').innerText(), /ocean/);
    await page.locator('#query').fill('(');
    await page.getByRole('button', { name: 'Explore books' }).click();
    await page.waitForFunction(() => document.querySelector('#status').classList.contains('error'));
    assert.match(await page.locator('#status').innerText(), /parenthesis/i);
    await page.locator('[data-query="adventure"]').click();
    await page.waitForFunction(() => document.querySelectorAll('.book-card').length > 0);
    await page.screenshot({ path: path.join(output, 'desktop-results.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, 'mobile-results.png'), fullPage: true });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    assert.equal(overflow, false, 'Mobile layout must not overflow horizontally.');
    assert.deepEqual(errors, [], 'Browser JavaScript errors.');
    console.log('Browser checks passed: keyword, frequency ranking, recommendations, regex, invalid regex, mobile layout.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
