const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const draftKey = 'waybill.custom-stops.v1';
const errors = new WeakMap();

test.beforeEach(async ({ page }) => {
  errors.set(page, []);
  page.on('pageerror', error => errors.get(page).push(error.message));
  // CI never consumes public search quotas or downloads community map tiles.
  await page.route('https://tile.openstreetmap.org/**', route => route.abort());
  await page.goto('/live.html#real-data');
  await expect(page.locator('#engine-state')).toContainText('Engine ready');
  await expect(page.locator('#fetch-places')).toBeEnabled();
});
test.afterEach(async ({page}) => { expect(errors.get(page)).toEqual([]); });

async function addManual(page, name, lat, lon) {
  const disclosure = page.locator('details').filter({ has: page.locator('#custom-manual-form') });
  if (!(await disclosure.getAttribute('open'))) {
    if (!(await page.locator('#custom-name').isVisible())) await disclosure.locator('summary').click();
  }
  await page.getByLabel('Place name', {exact:true}).fill(name);
  await page.getByLabel('Latitude', {exact:true}).fill(String(lat));
  await page.getByLabel('Longitude', {exact:true}).fill(String(lon));
  await page.getByRole('button', {name:'Add coordinates', exact:true}).click();
}

test('custom draft restores, reorders, exports and clears without restoring a stale solve', async ({page}) => {
  await addManual(page, 'Test-only Jaipur depot', 26.9124, 75.7873);
  await addManual(page, 'Test-only Jaipur stop', 26.9239299, 75.8268692);
  await expect(page.locator('#custom-stops .place-row')).toHaveCount(2);
  await page.getByRole('button', {name:'Start and return at Test-only Jaipur stop', exact:true}).click();
  await page.reload();
  await expect(page.locator('#custom-draft-status')).toContainText('restored');
  await expect(page.locator('#custom-stops .place-row').first()).toContainText('Start / return · Test-only Jaipur stop');
  await expect(page.locator('#custom-coverage')).toContainText('match bundled road coverage');
  const download = page.waitForEvent('download');
  await page.getByRole('button', {name:'Export custom dataset', exact:true}).click();
  const exported = JSON.parse(fs.readFileSync(await (await download).path(), 'utf8'));
  expect(exported.places[0].name).toBe('Test-only Jaipur stop');
  expect(exported.provider).toBe('osrm');
  expect(exported.provenance.planning_assumptions.actual_orders).toBe(false);
  await page.getByRole('button', {name:'Use these stops in route planner ↗', exact:true}).click();
  await expect(page.locator('#result-status')).toContainText('Inputs changed');
  await page.getByRole('tab', {name:'Places & real data', exact:true}).click();
  page.once('dialog', dialog => dialog.dismiss());
  await page.getByRole('button', {name:'Clear saved stops', exact:true}).click();
  await expect(page.locator('#custom-stops .place-row')).toHaveCount(2);
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', {name:'Clear saved stops', exact:true}).click();
  await expect(page.locator('#custom-stops .place-row')).toHaveCount(0);
  await page.reload();
  await expect(page.locator('#custom-stops .place-row')).toHaveCount(0);
  expect(await page.evaluate(key => localStorage.getItem(key), draftKey)).toBeNull();
});

test('damaged or unavailable storage leaves usable controls and never silently overwrites a draft', async ({page}) => {
  await page.evaluate(key => localStorage.setItem(key, '{broken'), draftKey);
  await page.reload();
  await expect(page.locator('#custom-draft-status')).toContainText('Nothing was overwritten');
  expect(await page.evaluate(key => localStorage.getItem(key), draftKey)).toBe('{broken');
  await addManual(page, 'Test-only replacement kept in memory', 26.9124, 75.7873);
  expect(await page.evaluate(key => localStorage.getItem(key), draftKey)).toBe('{broken');
  await expect(page.locator('#custom-draft-status')).toContainText('not saved');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', {name:'Clear saved stops', exact:true}).click();
  await page.addInitScript(() => { Storage.prototype.setItem = () => { throw new DOMException('Test-only storage denied', 'QuotaExceededError'); }; });
  await page.reload();
  await addManual(page, 'Test-only unsaved place', 26.9124, 75.7873);
  await expect(page.locator('#custom-draft-status')).toContainText('not saved');
  await expect(page.locator('#custom-stops .place-row')).toHaveCount(1);
});

test('coverage distinguishes the Jaipur query inset and wider road area; search fixture can build input', async ({page}) => {
  await page.getByText('Check the supported road-routing area', {exact:true}).click();
  await expect(page.locator('#coverage-region')).toHaveValue('jaipur');
  await expect(page.locator('#coverage-map')).toHaveAttribute('aria-label', /western corridor.*26.72.*27.13/);
  await expect(page.locator('.coverage-boundary')).toHaveCount(1);
  await expect(page.locator('.coverage-query')).toHaveCount(1);
  await page.locator('#coverage-region').selectOption('monaco');
  await expect(page.locator('.coverage-boundary')).toHaveCount(1);
  await expect(page.locator('.coverage-query')).toHaveCount(0);
  await expect(page.locator('#coverage-map')).toContainText('boundaries coincide');
  await page.route('**/api/places/search', route => route.fulfill({json:{places:[{name:'Test-only public-search fixture',lat:26.9239299,lon:75.8268692,coordinate_kind:'test fixture'}]}}));
  await page.getByLabel('Place / address and city', {exact:true}).fill('Test-only Jaipur fixture');
  await page.getByRole('button', {name:'Search places', exact:true}).click();
  await page.getByRole('button', {name:'Add Test-only public-search fixture', exact:true}).click();
  await expect(page.locator('#custom-stops')).toContainText('Test-only public-search fixture');
});

test('real browser imports/exports settings, compares real roads and survives failed street tiles', async ({page}) => {
  await page.locator('#import-file').setInputFiles(path.join(__dirname, '../fixtures/import-config.json'));
  await expect(page.locator('#import-error')).toBeEmpty();
  await expect(page.locator('#solver')).toHaveValue('held_karp');
  await expect(page.locator('#budget')).toHaveValue('250');
  const download = page.waitForEvent('download');
  await page.getByText('Input, constraints & travel model', {exact:true}).click();
  await page.getByRole('button', {name:'Export input', exact:true}).click();
  const exported = JSON.parse(fs.readFileSync(await (await download).path(), 'utf8'));
  expect(exported.wall_time_ms).toBe(250);
  expect(exported.solver).toBe('held_karp');
  await page.locator('#import-file').setInputFiles(path.join(__dirname, '../fixtures/import-invalid.csv'));
  await expect(page.locator('#import-error')).not.toBeEmpty();
  await page.locator('#dataset-selector').selectOption('sample');
  await page.getByRole('button', {name:'Compare all algorithms & routes', exact:true}).click();
  await expect(page.locator('#comparison-summary')).toContainText('Optimal');
  await expect(page.locator('.comparison-map')).toHaveCount(3);
  await page.getByRole('checkbox', {name:'Street backgrounds',exact:true}).check();
  await expect(page.locator('.comparison-map .street-tiles image').first()).toBeAttached();
  await expect(page.locator('.comparison-map-options [role="status"]')).toContainText('unavailable');
  await page.getByRole('checkbox', {name:'Street backgrounds',exact:true}).uncheck();
  await expect(page.locator('.street-tiles')).toHaveCount(0);
  await page.getByRole('button', {name:'Open in route explorer ↗',exact:true}).first().click();
  await page.getByRole('checkbox', {name:'Street background',exact:true}).check();
  await expect(page.locator('#street-status')).toContainText('unavailable');
  await expect(page.locator('#route-map .route-leg')).not.toHaveCount(0);
  await page.getByRole('checkbox', {name:'Street background',exact:true}).uncheck();
  await expect(page.locator('#route-map .street-tiles')).toHaveCount(0);
  await page.locator('#route-map').focus();
  await page.locator('#route-map').press('+');
  await page.locator('#route-map').press('Escape');
  const size = await page.evaluate(() => ({width:innerWidth,scroll:document.documentElement.scrollWidth}));
  expect(size.scroll).toBeLessThanOrEqual(size.width + 1);
});
