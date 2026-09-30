---
name: remote-browser
description: Cloud browser on the user's own Cloudflare account. Use to read a page that needs JavaScript or a real browser (returns title, text, links), to give the user a live remote browser for a manual login or CAPTCHA, or to manage deployments (/remote-browser deploy|list|status|delete).
---

# remote-browser

A Worker on the user's Cloudflare account that drives a cloud Chrome (Cloudflare Browser Run). The source is bundled in [template/](template/); [scripts/deploy.sh](scripts/deploy.sh) deploys it under a name the user chooses, and [scripts/instances.sh](scripts/instances.sh) manages the recorded deployments.

Each deployment is recorded in `~/.config/remote-browser/instances/<name>/`: `config.json` (`name`, `url`, `dir`, `deployedAt`) and `token` (mode 600). The token is a secret: read it from the file when calling the API, never paste it into chat.

Script paths below are relative to this skill's base directory (shown when the skill loads), so run them from there or with that directory as a prefix.

## Route

Look at the first word of the arguments after `/remote-browser`:

| Arguments | Action |
|---|---|
| `list` | [List](#list) |
| `status [name]` | [Status](#status) |
| `delete <name>` | [Delete](#delete) |
| `deploy [name]`, or none | [Setup](#setup) (a given name skips the name question) |
| anything else | Show this table and stop |

With no arguments and a browsing task (read a page, log in), go to [Use](#use).

## Output format

Present every subcommand result and the final deploy report as a tree in a fenced code block, with `├──` / `└──` connectors, not as prose. `instances.sh list|status|delete` already print trees: show them verbatim and add only nodes, not paragraphs. Keep any explanation to one short line after the block.

## List

Run `scripts/instances.sh list` and show its tree (per instance: URL, whether the page answers, deploy time). It reads only this machine's records; Workers deployed elsewhere don't appear.

## Status

`instances.sh status <name>`. With no name: use the only recorded instance, or ask which if there are several (`list` first). It reports whether the page answers, browser time used today, active sessions, and when a spent quota recovers. If it says the Worker predates `/status`, offer to redeploy it (`deploy <name>`, which updates in place).

## Delete

Irreversible: the Worker is removed from Cloudflare and its token from this machine. Run `instances.sh list`, confirm the exact name with AskUserQuestion, and only then run `instances.sh delete <name>`. Report the result. If it fails on authentication, do the [Cloudflare login](#2-cloudflare-login) step first; with several accounts, put `CLOUDFLARE_ACCOUNT_ID=<id>` in front of the command.

## Setup

### 0. Check the environment

Run `scripts/check-env.sh` before asking anything. Exit 0 → continue.

Otherwise it lists what's missing (Node.js 22.18+ built with TypeScript support, npm, curl) and prints `INSTALL_CMD` when it has one: a package-manager command for a missing `curl`, or `scripts/install-node.sh` for a Node.js problem. The script downloads an official Node.js 22 (about 30 MB, checksum-verified) into `~/.local/share/remote-browser/.node`, needs no `sudo` and changes nothing else; the other scripts then use it automatically. `cf` itself is not checked or installed up front: `npx --yes` fetches it for the login step and `npm install` puts a pinned copy in the Worker's folder. Ask the user with AskUserQuestion whether to install, showing the exact command:

- **Yes**: commands that need `sudo` can't take a password here, so have the user run it with `! <INSTALL_CMD>`; commands that don't (`install-node.sh`, `brew`) you may run. Then rerun the check.
- **No**, or `INSTALL_CMD` is empty: stop and tell them what to install manually (for Node.js, a build from nodejs.org or nvm), then rerun the check.

**Done when:** `check-env.sh` exits 0.

### 1. Collect parameters

Ask with AskUserQuestion; don't guess:

- **Worker name** (skip if given as an argument): lowercase letters, digits, dashes; default `remote-browser`. It becomes the `<name>.<subdomain>.workers.dev` address and must be free in their account.
- **API token**: offer to generate one (`node -e "console.log(require('crypto').randomBytes(24).toString('base64url'))"`, recommended) or let them supply one (16+ chars). This is the only thing protecting the Worker's public URL from spending their browser quota.

If `instances/<name>/` already exists, ask whether to update that deployment in place (`FORCE=1`, and offer to keep its saved token) or pick another name.

Tell them before deploying: Browser Run's free plan gives 10 browser-minutes a day and 3 concurrent browsers; sustained use needs Workers Paid.

**Done when:** you hold a valid name and a token of 16+ characters.

### 2. Cloudflare login

Run `npx --yes cf@latest auth whoami` (`--yes` skips the npx download prompt; `cf` isn't installed yet at this point). It exits 0 either way: if the JSON says `"authenticated": false`, have the user run `! npx --yes cf@latest auth login` (browser OAuth, only they can complete it; add `--no-browser` on a remote machine), then re-check. `cf` keeps its own credentials and doesn't reuse a Wrangler login, so someone who used Wrangler before still signs in once. If `accounts` lists more than one, ask which to use and put `CLOUDFLARE_ACCOUNT_ID=<id>` in front of the deploy command: without a terminal `cf` can't ask.

### 3. Deploy

```bash
WORKER_TOKEN='<token>' scripts/deploy.sh <name>
```

Add `FORCE=1` only to update an existing deployment. Exit codes: `2` not logged in (step 2 again), `3` name taken in the Cloudflare account (ask for another), `4` bad input (fix and rerun). The script installs dependencies, generates types and typechecks, deploys with the token as a secret, and records the instance; its last line is `WORKER_URL=<url>`.

### 4. Verify and report

Smoke-test with `/fetch?url=https://example.com` (see [Use](#use)); expect HTTP 200 and title `Example Domain`. Interpret failures:

- **HTTP 429** (`Browser Run rate limit or daily quota reached`): the deployment is fine; the account's Browser Run quota is used up (free plan: 10 browser-minutes per day, 3 concurrent browsers, one new browser per 10 seconds). Tell the user this explicitly, include the estimated recovery time from the response, and mention that Workers Paid removes the daily cap. Wait about 15 seconds and retry once to rule out the per-10-seconds limit; if it persists, report the deployment as successful but unverified.
- **HTTP 401**: the token sent doesn't match the saved one; recheck the instance's `token` file.
- **Other 5xx**: retry once, then read the error text in the response body (`details`, or `error` on `/status`).

**Done when:** the smoke test passes, or fails only with the 429 quota case above. Report as a tree, for example:

```
deployed <name>
├── url: https://<name>.<subdomain>.workers.dev
├── token file: ~/.config/remote-browser/instances/<name>/token
├── smoke test: passed | quota exhausted (recovers <time UTC>) | failed (<reason>)
└── next: open the URL and paste the token once
```

## Use

Pick the instance: the only one recorded, or ask which (`instances.sh list`). Read `url` from its `config.json` and the token from its `token` file.

- **Read a page**: `GET /fetch?url=<target>` with header `Authorization: Bearer <token>` → JSON `{url, finalUrl, title, text, links}`. `text` prefers `<article>`/`<main>`, so navigation chrome can leak in.
- **Interactive session** (login, CAPTCHA, 2FA, anything needing a human): `POST /session?url=<optional start page>` → `{sessionId, liveViewUrl}`. Give the user `liveViewUrl` to open; it grants full control of that browser, so treat it as a secret. Or they open the Worker URL and click "Open remote browser". Always end with `DELETE /session/<sessionId>`; otherwise it runs until it idles out (max 10 minutes) and burns browser time.
- **Quota check**: `GET /status` (same header) returns browser time used today and the recovery time; it doesn't consume browser time.

## Limits

- Every operation is subject to the account quota: a 429 from any endpoint means the daily browser time or the per-10-seconds rate is exhausted; say so plainly instead of retrying in a loop.
- Google and other heavily defended sites block Cloudflare's datacenter IPs ("unusual traffic" page). Use a search API instead of scraping results pages.
- The egress country can't be pinned: `location` returns 403 unless Cloudflare has enabled geoegress for the account.
- Sessions idle out after 60 seconds by default; the `/session` endpoint extends this to 10 minutes.
- Only automate sites and accounts the user is entitled to use.
