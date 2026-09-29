import puppeteer from "@cloudflare/puppeteer";
import { HTML_PAGE } from "./page";

// page.evaluate() below runs inside the remote Chrome tab, not the Worker —
// tsconfig deliberately omits the "dom" lib (it would clash with Workers'
// own Request/Response globals), so DOM identifiers are declared loosely here.
declare const document: any;

const SESSION_MS = 600_000;
const FREE_DAILY_BROWSER_SECONDS = 600;

interface PageLink {
  href: string;
  text: string;
}

interface FetchResult {
  url: string;
  finalUrl: string;
  title: string;
  text: string;
  links: PageLink[];
}

function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.ceil((totalSeconds % 3600) / 60);
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

// Browser Run's daily quota resets at 00:00 UTC.
function secondsUntilUtcMidnight(): number {
  const now = new Date();
  const nextMidnight = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1);
  return Math.ceil((nextMidnight - now.getTime()) / 1000);
}

async function browserErrorResponse(env: Env, error: unknown, fallback: string): Promise<Response> {
  const details = error instanceof Error ? error.message : String(error);
  if (!/code: 429|status=429|rate limit/i.test(details)) {
    return jsonResponse({ error: fallback, details }, 502);
  }

  let retryAfterSeconds = Number(/retryAfter=(\d+)/.exec(details)?.[1]);
  if (!Number.isFinite(retryAfterSeconds)) {
    try {
      const limits = await env.BROWSER.limits();
      if (limits.timeUntilNextAllowedBrowserAcquisition > 0) {
        retryAfterSeconds = limits.timeUntilNextAllowedBrowserAcquisition;
      } else if ((limits.usedBrowserTimeSeconds ?? 0) >= FREE_DAILY_BROWSER_SECONDS) {
        // limits() reports no wait once the daily quota is spent.
        retryAfterSeconds = secondsUntilUtcMidnight();
      }
    } catch {
      retryAfterSeconds = NaN;
    }
  }

  let message =
    "Browser Run rate limit or daily quota reached. Free plan: 10 browser-minutes per day, 3 concurrent browsers, one new browser per 10 seconds. Wait for the reset, or upgrade to Workers Paid.";
  const headers: Record<string, string> = { "content-type": "application/json" };
  const body: Record<string, unknown> = { details };
  if (Number.isFinite(retryAfterSeconds) && retryAfterSeconds > 0) {
    const recoversAt = new Date(Date.now() + retryAfterSeconds * 1000).toISOString();
    message += ` Estimated recovery in ${formatDuration(retryAfterSeconds)} (${recoversAt}).`;
    body.retryAfterSeconds = retryAfterSeconds;
    body.estimatedRecovery = recoversAt;
    headers["retry-after"] = String(Math.ceil(retryAfterSeconds));
  }
  return new Response(JSON.stringify({ error: message, ...body }), { status: 429, headers });
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export default {
  async fetch(request, env): Promise<Response> {
    const { pathname, searchParams } = new URL(request.url);

    if (pathname === "/" && request.method === "GET") {
      return new Response(HTML_PAGE, { headers: { "content-type": "text/html; charset=utf-8" } });
    }

    const isSessionRoute = pathname === "/session" || pathname.startsWith("/session/");
    if (pathname !== "/fetch" && pathname !== "/status" && !isSessionRoute) {
      return jsonResponse({ error: "Not found. Use GET /fetch?url=..." }, 404);
    }

    const authorization = request.headers.get("authorization");
    if (authorization !== `Bearer ${env.API_TOKEN}`) {
      return jsonResponse({ error: "Unauthorized" }, 401);
    }

    if (pathname === "/status") {
      try {
        const limits = await env.BROWSER.limits();
        const exhausted = (limits.usedBrowserTimeSeconds ?? 0) >= FREE_DAILY_BROWSER_SECONDS;
        const recoverySeconds =
          limits.timeUntilNextAllowedBrowserAcquisition > 0
            ? limits.timeUntilNextAllowedBrowserAcquisition
            : exhausted
              ? secondsUntilUtcMidnight()
              : 0;
        return jsonResponse({
          ok: true,
          usedBrowserTimeSeconds: limits.usedBrowserTimeSeconds ?? null,
          freeDailyLimitSeconds: FREE_DAILY_BROWSER_SECONDS,
          activeSessions: limits.activeSessions.length,
          maxConcurrentSessions: limits.maxConcurrentSessions,
          allowedBrowserAcquisitions: limits.allowedBrowserAcquisitions,
          estimatedRecovery:
            recoverySeconds > 0 ? new Date(Date.now() + recoverySeconds * 1000).toISOString() : null,
        });
      } catch (error) {
        return jsonResponse({ ok: false, error: error instanceof Error ? error.message : String(error) }, 502);
      }
    }

    if (isSessionRoute) {
      try {
        if (pathname === "/session" && request.method === "POST") {
          const raw = searchParams.get("url");
          let start: string | undefined;
          if (raw) {
            const u = new URL(raw);
            if (u.protocol !== "http:" && u.protocol !== "https:") {
              return jsonResponse({ error: "Only http/https URLs are supported" }, 400);
            }
            start = u.toString();
          }
          const { sessionId, targets } = await env.BROWSER.acquire({
            keepAlive: SESSION_MS,
            targets: true,
          });
          const targetId = start
            ? (await env.BROWSER.devtools.newTarget(sessionId, start)).id
            : targets?.find((t) => t.type === "page")?.id;
          const view = await env.BROWSER.getLiveView(sessionId, {
            mode: "full",
            targetId,
            expiresInMs: SESSION_MS,
          });
          return jsonResponse({ sessionId, liveViewUrl: view.devtoolsFrontendUrl });
        }
        const match = pathname.match(/^\/session\/([\w-]+)$/);
        if (match && request.method === "DELETE") {
          return jsonResponse(await env.BROWSER.closeSession(match[1]));
        }
      } catch (error) {
        return browserErrorResponse(env, error, "Session request failed");
      }
      return jsonResponse({ error: "Use POST /session or DELETE /session/:id" }, 405);
    }

    const rawUrl = searchParams.get("url");
    if (!rawUrl) {
      return jsonResponse({ error: "Missing required 'url' query parameter" }, 400);
    }

    let target: URL;
    try {
      target = new URL(rawUrl);
    } catch {
      return jsonResponse({ error: "Invalid 'url' parameter" }, 400);
    }
    if (target.protocol !== "http:" && target.protocol !== "https:") {
      return jsonResponse({ error: "Only http/https URLs are supported" }, 400);
    }

    // No geo-egress pinning: passing location: "US" 403s with "Account is not
    // permitted to set a geoegress location" — that's an account entitlement,
    // not a per-request option, so it can't be worked around here.
    let browser: Awaited<ReturnType<typeof puppeteer.launch>> | undefined;
    try {
      browser = await puppeteer.launch(env.BROWSER);
      const page = await browser.newPage();
      await page.goto(target.toString(), {
        waitUntil: "domcontentloaded",
        timeout: 30_000,
      });

      const extracted = await page.evaluate(() => {
        const root =
          document.querySelector("article") ??
          document.querySelector("main") ??
          document.querySelector('[role="main"]') ??
          document.body;
        const links: PageLink[] = Array.from(document.querySelectorAll("a[href]"))
          .map((a: any) => ({
            href: a.href as string,
            text: ((a.textContent ?? "") as string).trim(),
          }))
          .filter((link: PageLink) => link.href.startsWith("http"));
        return {
          title: document.title as string,
          text: root.innerText as string,
          links,
        };
      });

      const result: FetchResult = {
        url: target.toString(),
        finalUrl: page.url(),
        title: extracted.title,
        text: extracted.text,
        links: extracted.links,
      };
      return jsonResponse(result);
    } catch (error) {
      return browserErrorResponse(env, error, "Failed to load page");
    } finally {
      await browser?.close();
    }
  },
} satisfies ExportedHandler<Env>;
