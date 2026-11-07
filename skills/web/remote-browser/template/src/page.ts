export const HTML_PAGE = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="color-scheme" content="light dark" />
<title>remote-browser</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: oklch(98.5% 0.004 255);
    --panel: oklch(96.2% 0.007 255);
    --field: oklch(100% 0 0);
    --ink: oklch(23% 0.02 255);
    --muted: oklch(47% 0.02 255);
    --border: oklch(89% 0.009 255);
    --accent: oklch(50% 0.18 262);
    --accent-hover: oklch(44% 0.18 262);
    --on-accent: oklch(99% 0 0);
    --error: oklch(52% 0.2 27);
    --live: oklch(56% 0.15 155);
    --sel: oklch(85% 0.08 262);
    --radius: 10px;
    --ease: cubic-bezier(0.22, 1, 0.36, 1);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: oklch(17% 0.012 255);
      --panel: oklch(21% 0.014 255);
      --field: oklch(14.5% 0.012 255);
      --ink: oklch(93% 0.008 255);
      --muted: oklch(72% 0.016 255);
      --border: oklch(31% 0.016 255);
      --accent: oklch(72% 0.14 262);
      --accent-hover: oklch(78% 0.13 262);
      --on-accent: oklch(17% 0.02 262);
      --error: oklch(73% 0.17 25);
      --live: oklch(74% 0.15 155);
      --sel: oklch(40% 0.1 262);
    }
  }
  * { box-sizing: border-box; }
  html { scrollbar-color: var(--border) transparent; }
  ::selection { background: var(--sel); color: var(--ink); }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    caret-color: var(--accent);
  }
  svg { width: 16px; height: 16px; flex: none; fill: none; stroke: currentColor; stroke-width: 1.75; stroke-linecap: round; stroke-linejoin: round; }
  :focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .shell { max-width: 1280px; margin: 0 auto; padding: 0 16px 48px; }

  /* Top bar */
  header {
    display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
    padding: 14px 0; border-bottom: 1px solid var(--border);
  }
  .brand { display: flex; align-items: center; gap: 10px; font-weight: 650; font-size: 15px; letter-spacing: -0.01em; }
  .brand svg { width: 20px; height: 20px; color: var(--accent); }
  .token { display: flex; align-items: center; gap: 8px; }
  .token label { font-size: 13px; color: var(--muted); white-space: nowrap; }
  .token input { width: 220px; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--border); flex: none; }
  .dot.on { background: var(--live); }

  /* Controls */
  input[type=text], input[type=url], input[type=password], input[type=search] {
    height: 40px; width: 100%; padding: 0 12px;
    font: inherit; font-size: 14px; color: var(--ink);
    background: var(--field); border: 1px solid var(--border); border-radius: var(--radius);
    transition: border-color 0.15s var(--ease);
  }
  input:hover { border-color: color-mix(in oklch, var(--muted) 55%, var(--border)); }
  input:focus-visible { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in oklch, var(--accent) 25%, transparent); }
  input::placeholder { color: var(--muted); opacity: 0.8; }
  .btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    height: 40px; padding: 0 16px; font: inherit; font-size: 14px; font-weight: 550;
    border-radius: var(--radius); border: 1px solid var(--border); background: var(--panel); color: var(--ink);
    cursor: pointer; white-space: nowrap; text-decoration: none;
    transition: background-color 0.15s var(--ease), border-color 0.15s var(--ease), transform 0.15s var(--ease);
  }
  .btn:hover:not(:disabled) { border-color: color-mix(in oklch, var(--muted) 55%, var(--border)); }
  .btn:active:not(:disabled) { transform: translateY(1px); }
  .btn:disabled { opacity: 0.5; cursor: default; }
  .btn.primary { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
  .btn.primary:hover:not(:disabled) { background: var(--accent-hover); border-color: var(--accent-hover); }
  .btn.small { height: 32px; padding: 0 10px; font-size: 13px; }
  .btn.danger:hover:not(:disabled) { border-color: var(--error); color: var(--error); }

  /* Command bar */
  .bar { display: flex; gap: 8px; margin-top: 24px; }
  .urlbox { position: relative; flex: 1; min-width: 0; }
  .urlbox svg { position: absolute; left: 12px; top: 12px; color: var(--muted); pointer-events: none; }
  .urlbox input { padding-left: 36px; }

  /* Status */
  #status:empty { display: none; }
  #status { margin-top: 12px; font-size: 13.5px; color: var(--muted); display: flex; align-items: center; gap: 8px; }
  #status.error { color: var(--error); }
  .spin { width: 14px; height: 14px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Remote session */
  #remote-box { display: none; margin-top: 16px; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; background: var(--panel); }
  .rbar { display: flex; align-items: center; gap: 12px; padding: 8px 8px 8px 14px; border-bottom: 1px solid var(--border); font-size: 13px; }
  .rbar .live { display: flex; align-items: center; gap: 8px; font-weight: 550; }
  .rbar .live .dot { background: var(--live); }
  #timer { color: var(--muted); font-variant-numeric: tabular-nums; }
  .rbar .spacer { flex: 1; }
  #remote-frame { display: block; width: 100%; height: calc(100dvh - 210px); min-height: 480px; border: 0; background: var(--field); }

  /* Result */
  #result { display: none; margin-top: 24px; }
  .rhead { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
  .rhead h2 { margin: 0; font-size: 20px; line-height: 1.3; letter-spacing: -0.015em; text-wrap: balance; }
  #r-meta { display: inline-block; margin-top: 2px; font-size: 13px; color: var(--muted); word-break: break-all; text-decoration: none; }
  #r-meta:hover { color: var(--accent); text-decoration: underline; text-underline-offset: 3px; }
  .cols { display: grid; grid-template-columns: minmax(0, 84ch) minmax(280px, 1fr); gap: 16px; align-items: start; }
  .pane { border: 1px solid var(--border); border-radius: var(--radius); background: var(--panel); min-width: 0; }
  .pane-h { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 13px; font-weight: 600; min-height: 53px; }
  .pane-h .count { color: var(--muted); font-weight: 450; font-variant-numeric: tabular-nums; }
  .pane-h input { height: 32px; font-size: 13px; width: 150px; }
  #r-text { margin: 0; padding: 16px; white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; font-size: 14.5px; line-height: 1.65; max-height: 62vh; overflow-y: auto; }
  #r-links { list-style: none; margin: 0; padding: 6px; max-height: 62vh; overflow-y: auto; }
  #r-links a { display: block; padding: 6px 8px; border-radius: 6px; font-size: 13.5px; color: var(--ink); text-decoration: none; word-break: break-word; }
  #r-links a small { display: block; color: var(--muted); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  #r-links a:hover { background: color-mix(in oklch, var(--accent) 10%, transparent); color: var(--accent); }
  #r-links .none { padding: 12px 8px; color: var(--muted); font-size: 13px; }

  @media (max-width: 900px) {
    .cols { grid-template-columns: minmax(0, 1fr); }
    #r-text, #r-links { max-height: 50vh; }
  }
  @media (max-width: 640px) {
    .token { width: 100%; } .token input { flex: 1; width: auto; }
    .bar { flex-direction: column; }
    .bar .btn { width: 100%; }
    #remote-frame { height: calc(100dvh - 260px); min-height: 360px; }
  }
  @media (prefers-reduced-motion: reduce) { .spin { animation-duration: 2s; } .btn { transition: none; } }
</style>
</head>
<body>
<div class="shell">
  <header>
    <div class="brand">
      <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="14" rx="2.5"/><path d="M8 21h8M12 18v3"/><path d="M7.5 9.5h9"/></svg>
      remote-browser
    </div>
    <div class="token">
      <span class="dot" id="token-dot" aria-hidden="true"></span>
      <label for="token">API token</label>
      <input id="token" type="password" autocomplete="off" spellcheck="false" />
    </div>
  </header>

  <div class="bar">
    <div class="urlbox">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/></svg>
      <input id="url" type="url" inputmode="url" autocomplete="off" spellcheck="false" placeholder="https://example.com" aria-label="URL" />
    </div>
    <button class="btn primary" id="go" type="button">Fetch</button>
    <button class="btn" id="remote" type="button">
      <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="14" rx="2.5"/><path d="M8 21h8M12 18v3"/></svg>
      Remote browser
    </button>
  </div>
  <div id="status" role="status" aria-live="polite"></div>

  <section id="remote-box" aria-label="Remote browser">
    <div class="rbar">
      <span class="live"><span class="dot"></span>Live</span>
      <span id="timer">10:00</span>
      <span class="spacer"></span>
      <a class="btn small" id="remote-link" target="_blank" rel="noopener noreferrer">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>
        New window
      </a>
      <button class="btn small danger" id="close-remote" type="button">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
        Close
      </button>
    </div>
    <iframe id="remote-frame" title="Remote browser"></iframe>
  </section>

  <section id="result">
    <div class="rhead">
      <div>
        <h2 id="r-title"></h2>
        <a id="r-meta" target="_blank" rel="noopener noreferrer"></a>
      </div>
      <button class="btn small" id="copy" type="button">
        <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></svg>
        <span id="copy-label">Copy text</span>
      </button>
    </div>
    <div class="cols">
      <div class="pane">
        <div class="pane-h">Text</div>
        <pre id="r-text"></pre>
      </div>
      <div class="pane">
        <div class="pane-h">
          <span>Links <span class="count" id="r-count"></span></span>
          <input id="filter" type="search" placeholder="Filter" aria-label="Filter links" />
        </div>
        <ul id="r-links"></ul>
      </div>
    </div>
  </section>
</div>
<script>
  const SESSION_SECONDS = 600;
  const $ = (id) => document.getElementById(id);
  const tokenEl = $('token'), urlEl = $('url'), goEl = $('go'), statusEl = $('status'), resultEl = $('result');
  const remoteEl = $('remote'), closeEl = $('close-remote'), boxEl = $('remote-box'), timerEl = $('timer');
  let sessionId = null, timerId = null, links = [];

  try { tokenEl.value = localStorage.getItem('remote_browser_token') || ''; } catch {}
  function syncDot() { $('token-dot').className = 'dot' + (tokenEl.value.trim() ? ' on' : ''); }
  tokenEl.addEventListener('input', syncDot);
  syncDot();

  function setStatus(msg, kind) {
    statusEl.className = kind || '';
    statusEl.textContent = '';
    if (kind === 'busy') { const s = document.createElement('span'); s.className = 'spin'; statusEl.appendChild(s); }
    if (msg) statusEl.appendChild(document.createTextNode(msg));
  }

  function errText(resp, data) {
    const msg = (data && data.error) || ('Request failed (' + resp.status + ')');
    return data && data.details ? msg + ' (' + data.details + ')' : msg;
  }

  function needToken() {
    const token = tokenEl.value.trim();
    if (!token) { setStatus('Enter the API token first', 'error'); tokenEl.focus(); return null; }
    try { localStorage.setItem('remote_browser_token', token); } catch {}
    return token;
  }

  function renderLinks() {
    const q = $('filter').value.trim().toLowerCase();
    const list = $('r-links');
    list.textContent = '';
    const shown = links.filter((l) => !q || (l.text + ' ' + l.href).toLowerCase().includes(q));
    $('r-count').textContent = q ? shown.length + ' / ' + links.length : String(links.length);
    if (!shown.length) {
      const li = document.createElement('li');
      li.className = 'none';
      li.textContent = 'No links';
      list.appendChild(li);
      return;
    }
    shown.forEach((link) => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = link.href; a.target = '_blank'; a.rel = 'noopener noreferrer';
      const t = document.createElement('span');
      t.textContent = link.text || link.href;
      a.appendChild(t);
      if (link.text) { const s = document.createElement('small'); s.textContent = link.href; a.appendChild(s); }
      li.appendChild(a);
      list.appendChild(li);
    });
  }

  async function run() {
    const token = needToken();
    const url = urlEl.value.trim();
    if (!token) return;
    if (!url) { setStatus('Enter a URL', 'error'); urlEl.focus(); return; }
    resultEl.style.display = 'none';
    goEl.disabled = true;
    setStatus('Loading…', 'busy');
    try {
      const resp = await fetch('/fetch?url=' + encodeURIComponent(url), { headers: { Authorization: 'Bearer ' + token } });
      const data = await resp.json();
      if (!resp.ok) { setStatus(errText(resp, data), 'error'); return; }
      setStatus('');
      $('r-title').textContent = data.title || '(no title)';
      const meta = $('r-meta');
      meta.textContent = data.finalUrl;
      meta.href = data.finalUrl;
      $('r-text').textContent = data.text;
      $('filter').value = '';
      links = (data.links || []).slice(0, 200);
      renderLinks();
      resultEl.style.display = 'block';
    } catch (err) {
      setStatus('Network error: ' + err, 'error');
    } finally {
      goEl.disabled = false;
    }
  }

  function tick(endAt) {
    const left = Math.max(0, Math.round((endAt - Date.now()) / 1000));
    timerEl.textContent = Math.floor(left / 60) + ':' + String(left % 60).padStart(2, '0');
    if (left === 0) hideRemote();
  }

  function hideRemote() {
    clearInterval(timerId); timerId = null; sessionId = null;
    $('remote-frame').src = 'about:blank';
    boxEl.style.display = 'none';
    remoteEl.disabled = false;
    closeEl.disabled = false;
  }

  async function openRemote() {
    const token = needToken();
    if (!token) return;
    setStatus('Starting remote browser…', 'busy');
    remoteEl.disabled = true;
    const url = urlEl.value.trim();
    try {
      const resp = await fetch('/session' + (url ? '?url=' + encodeURIComponent(url) : ''), { method: 'POST', headers: { Authorization: 'Bearer ' + token } });
      const data = await resp.json();
      if (!resp.ok) { setStatus(errText(resp, data), 'error'); remoteEl.disabled = false; return; }
      sessionId = data.sessionId;
      $('remote-frame').src = data.liveViewUrl;
      $('remote-link').href = data.liveViewUrl;
      boxEl.style.display = 'block';
      setStatus('');
      const endAt = Date.now() + SESSION_SECONDS * 1000;
      tick(endAt);
      clearInterval(timerId);
      timerId = setInterval(() => tick(endAt), 1000);
      boxEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (err) {
      setStatus('Network error: ' + err, 'error');
      remoteEl.disabled = false;
    }
  }

  async function closeRemote() {
    if (!sessionId) return;
    closeEl.disabled = true;
    try { await fetch('/session/' + sessionId, { method: 'DELETE', headers: { Authorization: 'Bearer ' + tokenEl.value.trim() } }); } catch {}
    hideRemote();
  }

  async function copyText() {
    try {
      await navigator.clipboard.writeText($('r-text').textContent);
      $('copy-label').textContent = 'Copied';
      setTimeout(() => { $('copy-label').textContent = 'Copy text'; }, 1500);
    } catch {}
  }

  remoteEl.addEventListener('click', openRemote);
  closeEl.addEventListener('click', closeRemote);
  goEl.addEventListener('click', run);
  $('copy').addEventListener('click', copyText);
  $('filter').addEventListener('input', renderLinks);
  urlEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') run(); });
  tokenEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') urlEl.focus(); });
</script>
</body>
</html>
`;
