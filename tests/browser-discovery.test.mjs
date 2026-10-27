import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {syncBuiltinESMExports} from 'node:module';
import {findChrome} from '../vendor/taste/skills/scripts/lib/cdp.mjs';

function withPaths(paths, environment, check) {
  const exists = fs.existsSync;
  const keys = ['CHROME_PATH', 'PUPPETEER_EXECUTABLE_PATH'];
  const saved = Object.fromEntries(keys.map(key => [key, process.env[key]]));
  try {
    for (const key of keys) {
      if (environment[key] === undefined) delete process.env[key];
      else process.env[key] = environment[key];
    }
    fs.existsSync = path => paths.includes(path);
    syncBuiltinESMExports();
    check();
  } finally {
    fs.existsSync = exists;
    syncBuiltinESMExports();
    for (const key of keys) {
      if (saved[key] === undefined) delete process.env[key];
      else process.env[key] = saved[key];
    }
  }
}

test('finds Claude container Chromium without either environment override', () => {
  withPaths(['/opt/pw-browsers/chromium'], {}, () =>
    assert.equal(findChrome(), '/opt/pw-browsers/chromium'));
});
test('honors an explicit browser path', () => {
  withPaths(['/custom/chrome', '/opt/pw-browsers/chromium'], {CHROME_PATH: '/custom/chrome'}, () =>
    assert.equal(findChrome(), '/custom/chrome'));
});
test('honors the existing Puppeteer override', () => {
  withPaths(['/custom/puppeteer', '/opt/pw-browsers/chromium'], {PUPPETEER_EXECUTABLE_PATH: '/custom/puppeteer'}, () =>
    assert.equal(findChrome(), '/custom/puppeteer'));
});
test('does not claim a browser exists when no candidate is installed', () => {
  withPaths([], {}, () => assert.equal(findChrome(), null));
});
