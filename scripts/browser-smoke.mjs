import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const base = 'http://127.0.0.1:18779';
const server = spawn(process.env.PLATFORM_PYTHON || 'python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '18779', '--no-access-log'], {
  cwd: root, env: {...process.env, APP_REVISION: 'browser-test', APP_ENV: 'local-test'}, stdio: ['ignore', 'ignore', 'pipe']
});
let startupError;
server.on('error', error => {startupError = error;});
let browser;
try {
  let ready = false;
  for (let attempt=0; attempt<100; attempt++) {
    if (startupError) throw startupError;
    try {if ((await fetch(`${base}/readyz`)).ok) {ready=true;break;}} catch {}
    await new Promise(resolve => setTimeout(resolve,100));
  }
  if (!ready) throw new Error('Application did not start');
  browser = await chromium.launch({headless:true,executablePath:process.env.PLATFORM_BROWSER || undefined,args:['--no-sandbox']});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base);
  await page.waitForFunction(() => document.querySelector('#health').textContent === 'Service ready');
  if ((await page.locator('#revision').innerText())!=='browser-test') throw new Error('Release not rendered');
  await page.click('button');
  await page.waitForFunction(() => document.querySelector('#result').textContent.includes('0.5 vCPU'));
  await mkdir(path.join(root,'verification'),{recursive:true});
  await page.screenshot({path:path.join(root,'verification/desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  if (await page.evaluate(() => document.documentElement.scrollWidth>innerWidth)) throw new Error('Mobile horizontal overflow');
  await page.screenshot({path:path.join(root,'verification/mobile.png'),fullPage:true});
  if (errors.length) throw new Error(errors.join('; '));
  console.log(JSON.stringify({release_rendered:true,capacity_flow:true,javascript_errors:0,mobile_horizontal_overflow:false}));
} finally {
  if (browser) await browser.close();
  server.kill();
}
