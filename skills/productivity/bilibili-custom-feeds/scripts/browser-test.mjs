// Drive headless Chrome via CDP: inject the userscript into bilibili.com with a
// real session and confirm a feed renders. Prints card count and a sample.
//
// Usage:
//   node browser-test.mjs <feedIndex> [userscriptPath] [cookiePath]
//
// Defaults: feedIndex 0, script ../assets/bili-custom-feeds.user.js, cookie
// file path from BILI_SESSDATA_FILE (must contain a SESSDATA value).
// Requires `google-chrome` on PATH and node >= 22 (global fetch, WebSocket).
//
// Pass criteria (exit 0): userscript injected, panel booted, the target feed
// settled, and it rendered at least one card. Exit 1 otherwise — including a
// settled-but-empty feed: an empty grid is indistinguishable from a blocked or
// broken fetch, so treat it as a failure. Set BCF_ALLOW_EMPTY=1 to pass a
// legitimately-empty feed (the console log is printed either way for manual
// inspection).
import fs from 'fs';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const fi = parseInt(process.argv[2] || '0', 10);
const scriptPath = process.argv[3] || path.join(here, '..', 'assets', 'bili-custom-feeds.user.js');
const cookiePath = process.argv[4] || process.env.BILI_SESSDATA_FILE;
if (!cookiePath) { console.error('need a cookie file path as arg 3 or BILI_SESSDATA_FILE'); process.exit(2); }
let sess;
try {
  sess = fs.readFileSync(cookiePath, 'utf8').trim().replace(/^SESSDATA=/, '');
} catch {
  console.error(`cookie file not found or unreadable: ${cookiePath}`); process.exit(2);
}
if (!sess) { console.error(`cookie file is empty: ${cookiePath}`); process.exit(2); }
let SCRIPT;
try {
  SCRIPT = fs.readFileSync(scriptPath, 'utf8');
} catch {
  console.error(`userscript not found or unreadable: ${scriptPath}`); process.exit(2);
}

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

const gridState = ws => send(ws, 'Runtime.evaluate', { expression: `(()=>{const g=document.getElementById('bcf-grid');
  if(!g) return JSON.stringify({noGrid:true});
  return JSON.stringify({c:g.querySelectorAll('.bcf-card').length,
   busy:[...g.querySelectorAll('.bcf-empty')].some(e=>/正在拉取/.test(e.textContent)),
   empty:[...g.querySelectorAll('.bcf-empty')].map(e=>e.textContent).join('|')});})()`, returnByValue: true }).then(s => JSON.parse(s.result?.value || '{}'));

// Poll until the grid settles (not busy) or timeout. Returns the last state.
async function waitSettled(ws, maxMs) {
  let v = {};
  for (let t = 0; t < maxMs; t += 2000) {
    v = await gridState(ws);
    if (!v.busy) break;
    await sleep(2000);
  }
  return v;
}

let failed = false;
const fail = msg => { failed = true; console.error('FAIL: ' + msg); };

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
  if (inj.result?.value !== 'ok') fail('userscript inject failed: ' + inj.result?.value);
  else console.log('inject: ok');
  const boot = await send(ws, 'Runtime.evaluate', { expression: `(()=>{const f=document.getElementById('bcf-fab'); if(!f) return 'no-fab'; f.click(); return 'ok';})()`, returnByValue: true });
  if (boot.result?.value !== 'ok') fail('panel did not boot: ' + boot.result?.value);
  else console.log('panel: booted');
  // Wait for the opening feed to fully settle before switching tabs, or its
  // slower result lands last and overwrites the grid (a real trap in testing).
  await waitSettled(ws, 120000);
  await send(ws, 'Runtime.evaluate', { expression: `document.querySelectorAll('.bcf-tab')[${fi}]?.click(); 'ok'` });
  // Poll the target feed until it settles instead of sleeping a fixed 30 s.
  const v = await waitSettled(ws, 60000);
  if (v.noGrid) fail('grid element missing');
  if (v.busy) fail('feed still fetching at timeout');
  const r = await send(ws, 'Runtime.evaluate', { expression: `(()=>{const g=document.getElementById('bcf-grid');
    const cards=[...g.querySelectorAll('.bcf-card')];
    return JSON.stringify({n:cards.length,
     empty:[...g.querySelectorAll('.bcf-empty')].map(e=>e.textContent).join('|'),
     sample:cards.slice(0,10).map(c=>c.querySelector('.bcf-title')?.textContent?.slice(0,36)+' | '+(c.querySelector('.bcf-src')?.textContent||''))});})()`, returnByValue: true });
  console.log('feed' + fi + ':', r.result?.value);
  console.log('console logs:', logs.filter(l => l.includes('[bcf]')).slice(-10).join('\n'));
  if (v.c === 0) {
    const blocked = logs.some(l => /BLOCKED|失败|code -?\d/.test(l));
    if (blocked) fail('feed rendered empty and the console shows fetch failures/blocks');
    else if (process.env.BCF_ALLOW_EMPTY === '1') console.log('NOTE: empty feed accepted via BCF_ALLOW_EMPTY=1');
    else fail('feed rendered empty (set BCF_ALLOW_EMPTY=1 only if you have verified it is legitimately empty)');
  } else {
    console.log('cards: ' + v.c);
  }
  ws.close();
} catch (e) {
  fail('driver error: ' + (e?.message || e));
} finally {
  chrome.kill();
  process.exit(failed ? 1 : 0);
}
