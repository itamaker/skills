export const HTML_PAGE = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>remote-browser</title>
<style>
  :root {
    --bg: #ffffff;
    --fg: #1a1a1a;
    --muted: #6b7280;
    --border: #e5e7eb;
    --accent: #2563eb;
    --error: #dc2626;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #15161a;
      --fg: #e8e8ea;
      --muted: #9aa0ab;
      --border: #2c2d33;
      --accent: #5b9dff;
      --error: #f87171;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 24px 16px 64px;
    background: var(--bg);
    color: var(--fg);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  main { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 18px; margin: 0 0 20px; }
  .field { margin-bottom: 12px; }
  label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 4px; }
  input {
    width: 100%;
    padding: 10px 12px;
    font-size: 15px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: transparent;
    color: var(--fg);
  }
  input:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
  button {
    margin-top: 4px;
    padding: 10px 18px;
    font-size: 15px;
    border: none;
    border-radius: 8px;
    background: var(--accent);
    color: #fff;
    cursor: pointer;
  }
  button:disabled { opacity: 0.6; cursor: default; }
  #remote-box {
    display: none;
    margin-top: 20px;
    width: min(1600px, calc(100vw - 32px));
    position: relative;
    left: 50%;
    transform: translateX(-50%);
  }
  #remote-frame {
    display: block;
    width: 100%;
    height: calc(100vh - 120px);
    min-height: 600px;
    border: 1px solid var(--border);
    border-radius: 8px;
  }
  #status { margin-top: 12px; font-size: 14px; color: var(--muted); }
  #status.error { color: var(--error); }
  #result { margin-top: 28px; display: none; }
  #result h2 { font-size: 17px; margin: 0 0 4px; }
  #result .meta { font-size: 13px; color: var(--muted); margin-bottom: 16px; word-break: break-all; }
  #result .text {
    white-space: pre-wrap;
    line-height: 1.6;
    font-size: 14.5px;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    max-height: 420px;
    overflow-y: auto;
  }
  #result .links { margin-top: 18px; }
  #result .links h3 { font-size: 13px; color: var(--muted); margin: 0 0 8px; font-weight: 600; }
  #result .links ul { list-style: none; margin: 0; padding: 0; max-height: 200px; overflow-y: auto; }
  #result .links li { margin-bottom: 6px; font-size: 13.5px; }
  #result .links a { color: var(--accent); text-decoration: none; word-break: break-all; }
  #result .links a:hover { text-decoration: underline; }
</style>
</head>
<body>
<main>
  <h1>remote-browser</h1>
  <div class="field">
    <label for="token">API Token</label>
    <input id="token" type="password" autocomplete="off" placeholder="Bearer token" />
  </div>
  <div class="field">
    <label for="url">URL</label>
    <input id="url" type="url" placeholder="https://example.com" />
  </div>
  <button id="go">Fetch</button>
  <button id="remote">Open remote browser</button>
  <button id="close-remote" style="display:none">Close remote browser</button>
  <div id="status"></div>
  <div id="remote-box">
    <div class="meta"><a id="remote-link" target="_blank" rel="noopener noreferrer">Open in new window</a> · session lasts up to 10 minutes</div>
    <iframe id="remote-frame"></iframe>
  </div>

  <div id="result">
    <h2 id="r-title"></h2>
    <div class="meta" id="r-meta"></div>
    <div class="text" id="r-text"></div>
    <div class="links">
      <h3>Links</h3>
      <ul id="r-links"></ul>
    </div>
  </div>
</main>
<script>
  const tokenEl = document.getElementById('token');
  const urlEl = document.getElementById('url');
  const goEl = document.getElementById('go');
  const statusEl = document.getElementById('status');
  const resultEl = document.getElementById('result');

  tokenEl.value = localStorage.getItem('remote_browser_token') || '';

  function errText(resp, data) {
    const msg = (data && data.error) || ('Request failed (' + resp.status + ')');
    return data && data.details ? msg + ' (' + data.details + ')' : msg;
  }

  async function run() {
    const token = tokenEl.value.trim();
    const url = urlEl.value.trim();
    statusEl.className = '';
    resultEl.style.display = 'none';

    if (!token) { statusEl.textContent = 'Enter the API token first'; statusEl.className = 'error'; return; }
    if (!url) { statusEl.textContent = 'Enter a URL'; statusEl.className = 'error'; return; }

    try { localStorage.setItem('remote_browser_token', token); } catch {}

    goEl.disabled = true;
    statusEl.textContent = 'Loading…';

    try {
      const resp = await fetch('/fetch?url=' + encodeURIComponent(url), {
        headers: { Authorization: 'Bearer ' + token },
      });
      const data = await resp.json();
      if (!resp.ok) {
        statusEl.textContent = errText(resp, data);
        statusEl.className = 'error';
        return;
      }
      statusEl.textContent = '';
      document.getElementById('r-title').textContent = data.title || '(no title)';
      document.getElementById('r-meta').textContent = data.finalUrl;
      document.getElementById('r-text').textContent = data.text;
      const linksEl = document.getElementById('r-links');
      linksEl.innerHTML = '';
      (data.links || []).slice(0, 200).forEach((link) => {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = link.href;
        a.textContent = link.text || link.href;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        li.appendChild(a);
        linksEl.appendChild(li);
      });
      resultEl.style.display = 'block';
    } catch (err) {
      statusEl.textContent = 'Network error: ' + err;
      statusEl.className = 'error';
    } finally {
      goEl.disabled = false;
    }
  }

  const remoteEl = document.getElementById('remote');
  const closeEl = document.getElementById('close-remote');
  const boxEl = document.getElementById('remote-box');
  let sessionId = null;

  async function openRemote() {
    const token = tokenEl.value.trim();
    if (!token) { statusEl.textContent = 'Enter the API token first'; statusEl.className = 'error'; return; }
    try { localStorage.setItem('remote_browser_token', token); } catch {}
    statusEl.className = '';
    statusEl.textContent = 'Starting remote browser…';
    remoteEl.disabled = true;
    const url = urlEl.value.trim();
    try {
      const resp = await fetch('/session' + (url ? '?url=' + encodeURIComponent(url) : ''), {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + token },
      });
      const data = await resp.json();
      if (!resp.ok) {
        statusEl.textContent = errText(resp, data);
        statusEl.className = 'error';
        remoteEl.disabled = false;
        return;
      }
      sessionId = data.sessionId;
      document.getElementById('remote-frame').src = data.liveViewUrl;
      document.getElementById('remote-link').href = data.liveViewUrl;
      boxEl.style.display = 'block';
      closeEl.style.display = '';
      statusEl.textContent = '';
    } catch (err) {
      statusEl.textContent = 'Network error: ' + err;
      statusEl.className = 'error';
      remoteEl.disabled = false;
    }
  }

  async function closeRemote() {
    if (!sessionId) return;
    closeEl.disabled = true;
    try {
      await fetch('/session/' + sessionId, {
        method: 'DELETE',
        headers: { Authorization: 'Bearer ' + tokenEl.value.trim() },
      });
    } catch {}
    sessionId = null;
    document.getElementById('remote-frame').src = 'about:blank';
    boxEl.style.display = 'none';
    closeEl.style.display = 'none';
    closeEl.disabled = false;
    remoteEl.disabled = false;
  }

  remoteEl.addEventListener('click', openRemote);
  closeEl.addEventListener('click', closeRemote);
  goEl.addEventListener('click', run);
  urlEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') run(); });
</script>
</body>
</html>
`;
