# remote-browser

A Claude Code skill that gives Claude a real cloud browser of its own. It deploys the browser to your Cloudflare account with one command, remembers each deployment, and then Claude can use it whenever a task needs a page that plain fetching can't handle.

## What Claude can do with it

- **Read a page that needs JavaScript or a real browser**, and get back its title, text and links.
- **Hand you a live remote browser** when a task needs a human, such as logging in or solving a CAPTCHA. You operate it in your own browser tab; Claude carries on afterwards.
- **Report its own budget**: how much browser time is left today and when it recovers.

## Quick start

1. Run `/remote-browser deploy`. Claude checks your environment, asks for a Worker name and an API token, has you sign in to Cloudflare once, deploys, and smoke-tests it.
2. Ask Claude to read a page, or to open a remote browser so you can log in somewhere. It finds your deployment on its own.
3. Run `/remote-browser status` any time to see the quota.

You can also open the Worker's address in a browser for a small web UI: paste the token once, then fetch pages or open a remote browser by hand.

## Commands

| Command | What it does |
|---|---|
| `/remote-browser deploy [name]` | Deploy a new Worker, or update an existing one in place |
| `/remote-browser list` | List the deployments recorded on this machine |
| `/remote-browser status [name]` | Show reachability, browser time used today, active sessions and recovery time |
| `/remote-browser delete <name>` | Delete the Worker and its local record; asks first, cannot be undone |

Results come back as trees:

```
remote-browser-test
├── url: https://remote-browser-test.<subdomain>.workers.dev
├── page: HTTP 200
└── browser quota
    ├── used today: 312s of 600s (free plan)
    ├── sessions: 0 active / 4 max
    └── recovery: not limited right now
```

`list` only knows about deployments made through this skill on this machine.

## What `deploy` does

1. Checks Node.js 18+, npm and curl, and offers an install command if one is missing.
2. Asks for a Worker name (lowercase letters, digits, dashes) and an API token. The default is a generated random token.
3. Makes sure you are signed in to Cloudflare, and has you run `wrangler login` if not.
4. Installs dependencies, typechecks the Worker, uploads the token as a secret, and deploys.
5. Records the deployment locally and smoke-tests it.
6. Reports the address, the token file and the test result.

The token is never printed in chat. It is stored with mode 600 and sent to the Worker only as a request header.

## How Claude uses a deployment

Claude reads the address and token from the local record and calls the Worker's HTTP API. Every endpoint except the web page needs `Authorization: Bearer <token>`.

| Endpoint | Purpose |
|---|---|
| `GET /fetch?url=<target>` | Title, text and links of the rendered page |
| `POST /session?url=<start page>` | Start a remote browser; returns a live-view link for you to open |
| `DELETE /session/<id>` | Close a session (Claude always closes the ones it opens) |
| `GET /status` | Browser time used today and recovery time; costs no browser time |

A live-view link gives full control of that browser, so treat it like a password. Sessions end on their own after 10 minutes.

## Files

```
<skills dir>/remote-browser/              the skill (wherever your install puts it)
├── SKILL.md                              instructions Claude follows
├── README.md                             this file
├── scripts/
│   ├── check-env.sh                      environment check
│   ├── deploy.sh                         deploy and record an instance
│   └── instances.sh                      list / status / delete
└── template/                             the Worker source that gets deployed

~/.config/remote-browser/instances/<name>/     one folder per deployment
├── config.json                           name, address, deploy time
└── token                                 API token (mode 600)

~/.local/share/remote-browser/<name>/          copy of the source that was deployed
```

To change the Worker, edit `template/` and run `/remote-browser deploy <name>`; it updates in place. To rotate a token, redeploy the same name and choose a new one.

## Good to know

- **Cloudflare**: each deployment is a Cloudflare Worker using Browser Run (formerly Browser Rendering) for the browser, `@cloudflare/puppeteer` to drive it, and a Worker secret for the token. Deploy, login and delete go through the Wrangler CLI.
- **Quota**: browser time is limited per Cloudflare account. The free plan allows 10 minutes a day (resets 00:00 UTC), one new browser per 10 seconds and 3 at a time. Past that, every endpoint answers HTTP 429 with an estimated recovery time. A paid Cloudflare plan is recommended for regular use; see Cloudflare's pricing page for details.
- **Blocked sites**: heavily defended sites, Google in particular, refuse Cloudflare's datacenter addresses. Use a search API instead of scraping results.
- **Region**: the browser's country can't be chosen; it depends on Cloudflare's routing.
- **Fair use**: only automate sites and accounts you are entitled to use.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| HTTP 429 with a recovery time | Browser quota spent; wait for the reset |
| HTTP 401 | Token differs from the deployed one; check the instance's `token` file |
| `status` says the Worker predates `/status` | Older deployment; run `/remote-browser deploy <name>` |
| `deploy` says not logged in | Run `npx --yes wrangler@4 login` and retry |
| `deploy` says the name already exists | Pick another name, or update that one |
