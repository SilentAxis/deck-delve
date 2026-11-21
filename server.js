'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const { WebSocketServer } = require('ws');
const E = require('./engine');

const PORT = Number(process.env.PORT) || 8080;
const DATA = process.env.DATA_DIR || path.join(__dirname, 'data');
const FILE = path.join(DATA, 'game.json');

let state;
try { state = JSON.parse(fs.readFileSync(FILE, 'utf8')); console.log('Resumed saved game'); } catch { state = E.newState(); }
function save() {
  try { fs.mkdirSync(DATA, { recursive: true }); fs.writeFileSync(FILE + '.tmp', JSON.stringify(state)); fs.renameSync(FILE + '.tmp', FILE); }
  catch (e) { console.error('save failed:', e.message); }
}

const html = fs.readFileSync(path.join(__dirname, 'public', 'index.html'));
const server = http.createServer((req, res) => {
  if (req.url === '/healthz') { res.writeHead(200); res.end('ok'); return; }
  const art = /^\/art\/([a-z0-9-]+)\.svg$/.exec(req.url.split('?')[0]);
  if (art) {
    const file = path.join(__dirname, 'public', 'art', art[1] + '.svg');
    fs.readFile(file, (e, buf) => {
      if (e) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'content-type': 'image/svg+xml', 'cache-control': 'public, max-age=86400' });
      res.end(buf);
    });
    return;
  }
  res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' });
  res.end(html);
});

const wss = new WebSocketServer({ server, path: '/ws', maxPayload: 16 * 1024 });
const MAX_CLIENTS = Number(process.env.MAX_CLIENTS) || 40;
const online = () => new Set([...wss.clients].map((c) => c.token).filter(Boolean));
let pending = false;
function broadcast() { if (!pending) { pending = true; setImmediate(flush); } }
function flush() {
  pending = false;
  const on = online();
  for (const c of wss.clients) if (c.readyState === 1 && c.token) c.send(JSON.stringify({ type: 'state', state: E.view(state, c.token, on) }));
}

wss.on('connection', (ws) => {
  if (wss.clients.size > MAX_CLIENTS) { ws.close(1013, 'Server full'); return; }
  ws.alive = true;
  ws.bucket = 20; ws.last = Date.now();
  ws.on('pong', () => { ws.alive = true; });
  ws.on('message', (raw) => {
    const now = Date.now(); // token bucket: ~10 messages/second, bursts of 20
    ws.bucket = Math.min(20, ws.bucket + (now - ws.last) / 100); ws.last = now;
    if (ws.bucket < 1) return;
    ws.bucket -= 1;
    let m; try { m = JSON.parse(raw); } catch { return; }
    if (m.type === 'hello') { ws.token = String(m.token || '').slice(0, 64) || null; broadcast(); return; }
    if (m.type !== 'act' || !ws.token) return;
    const backup = JSON.stringify(state);
    try { E.apply(state, ws.token, m.action || {}); save(); }
    catch (e) {
      state = JSON.parse(backup);
      if (!e.user) console.error(e);
      ws.send(JSON.stringify({ type: 'error', msg: e.user ? e.message : 'Something went wrong' }));
    }
    broadcast();
  });
  ws.on('close', broadcast);
});

// drop phones that went to sleep without closing the socket
setInterval(() => { for (const c of wss.clients) { if (!c.alive) { c.terminate(); continue; } c.alive = false; c.ping(); } }, 15000);

server.listen(PORT, () => console.log(`Deck Delve listening on :${PORT}`));
