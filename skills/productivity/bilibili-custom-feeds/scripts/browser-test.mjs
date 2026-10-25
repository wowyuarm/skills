// Drive headless Chrome via CDP: inject the userscript into bilibili.com with a
// real session and confirm a feed renders. Prints card count and a sample.
//
// Usage:
//   node browser-test.mjs <feedIndex> [userscriptPath] [cookiePath]
//
// Defaults: feedIndex 0, script ../assets/bili-custom-feeds.user.js, cookie
// file path from BILI_SESSDATA_FILE (must contain a SESSDATA value).
// Requires `google-chrome` on PATH and node >= 18 (global fetch, WebSocket).
import fs from 'fs';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const fi = parseInt(process.argv[2] || '0', 10);
const scriptPath = process.argv[3] || path.join(here, '..', 'assets', 'bili-custom-feeds.user.js');
const cookiePath = process.argv[4] || process.env.BILI_SESSDATA_FILE;
if (!cookiePath) { console.error('need a cookie file path as arg 3 or BILI_SESSDATA_FILE'); process.exit(2); }

const SCRIPT = fs.readFileSync(scriptPath, 'utf8');
const sess = fs.readFileSync(cookiePath, 'utf8').trim().replace(/^SESSDATA=/, '');
const PORT = 9400 + Math.floor(Math.random() * 90);
const UD = (process.env.TMPDIR || '/tmp') + '/bcf-test' + Date.now();

const chrome = spawn('google-chrome', ['--headless=new', '--disable-gpu', '--no-sandbox',
  '--remote-debugging-port=' + PORT, '--user-data-dir=' + UD, '--window-size=1280,900', 'about:blank'], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));
async function getWs() {
  for (let i = 0; i < 50; i++) {
    try {
      const r = await fetch('http://127.0.0.1:' + PORT + '/json');
      const t = await r.json();
      const p = t.find(x => x.type === 'page');
      if (p) return p.webSocketDebuggerUrl;
    } catch {}
    await sleep(300);
  }
  throw new Error('no cdp');
}
let id = 0, pending = new Map(), logs = [];
function send(ws, m, p = {}) { const mid = ++id; ws.send(JSON.stringify({ id: mid, method: m, params: p })); return new Promise((res, rej) => pending.set(mid, { res, rej })); }

try {
  const ws = new WebSocket(await getWs());
  await new Promise(r => ws.onopen = r);
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.method === 'Runtime.consoleAPICalled') logs.push(m.params.args.map(a => String(a.value ?? a.description ?? '')).join(' '));
    if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); }
  };
  await send(ws, 'Page.enable'); await send(ws, 'Network.enable'); await send(ws, 'Runtime.enable');
  await send(ws, 'Network.setCookie', { name: 'SESSDATA', value: sess, domain: '.bilibili.com', path: '/' });
  await send(ws, 'Page.navigate', { url: 'https://www.bilibili.com/' });
  await sleep(6000);
  const inj = await send(ws, 'Runtime.evaluate', { expression: `(()=>{try{ ${SCRIPT}; return 'ok'; }catch(e){return 'ERR:'+e.message}})()`, returnByValue: true });
  console.log('inject:', inj.result?.value);
  await send(ws, 'Runtime.evaluate', { expression: `document.getElementById('bcf-fab').click(); 'ok'` });
  // Wait for the opening feed to fully settle before switching tabs, or its
  // slower result lands last and overwrites the grid (a real trap in testing).
  for (let i = 0; i < 60; i++) {
    const s = await send(ws, 'Runtime.evaluate', { expression: `(()=>{const g=document.getElementById('bcf-grid');return JSON.stringify({c:g.querySelectorAll('.bcf-card').length,busy:[...g.querySelectorAll('.bcf-empty')].some(e=>/正在拉取/.test(e.textContent))});})()`, returnByValue: true });
    const v = JSON.parse(s.result?.value || '{}');
    if (!v.busy && v.c > 0) break;
    await sleep(2000);
  }
  await send(ws, 'Runtime.evaluate', { expression: `document.querySelectorAll('.bcf-tab')[${fi}]?.click(); 'ok'` });
  await sleep(30000);
  const r = await send(ws, 'Runtime.evaluate', { expression: `(()=>{const g=document.getElementById('bcf-grid');
    const cards=[...g.querySelectorAll('.bcf-card')];
    return JSON.stringify({n:cards.length,
     empty:[...g.querySelectorAll('.bcf-empty')].map(e=>e.textContent).join('|'),
     sample:cards.slice(0,10).map(c=>c.querySelector('.bcf-title')?.textContent?.slice(0,36)+' | '+(c.querySelector('.bcf-src')?.textContent||''))});})()`, returnByValue: true });
  console.log('feed' + fi + ':', r.result?.value);
  console.log('console logs:', logs.filter(l => l.includes('[bcf]')).slice(-10).join('\n'));
  ws.close();
} finally {
  chrome.kill();
  process.exit(0);
}
