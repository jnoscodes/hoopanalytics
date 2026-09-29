// Cloudflare Worker: a minimal relay to stats.nba.com.
//
// Why: stats.nba.com blocks AWS/GCP/Azure IP ranges, which is where
// Streamlit Community Cloud runs (see PROGRESS.md, task 1.9). This Worker
// runs on Cloudflare's own network instead; the app would send its
// requests here and the Worker forwards them to stats.nba.com.
//
// Request:  GET https://<worker>/stats/<endpoint>?<params>
//           with header  X-Relay-Key: <RELAY_KEY>
// Response: stats.nba.com's response (status + JSON body), unchanged.
//
// RELAY_KEY is a Worker secret (Settings -> Variables and Secrets). Without
// it, anyone who found the URL could use this as an open proxy and burn the
// free-tier quota.

const UPSTREAM = "https://stats.nba.com";
const TIMEOUT_MS = 20000;

// Same browser-like headers nba_api sends (nba_api/stats/library/http.py).
// Host/Connection/Accept-Encoding are left out: the Workers runtime sets
// those itself.
const NBA_HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
  Accept: "application/json, text/plain, */*",
  "Accept-Language": "en-US,en;q=0.5",
  Referer: "https://www.nba.com/",
  Origin: "https://www.nba.com",
  Pragma: "no-cache",
  "Cache-Control": "no-cache",
  "Sec-Ch-Ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
  "Sec-Ch-Ua-Mobile": "?0",
  "Sec-Fetch-Dest": "empty",
};

export default {
  async fetch(request, env) {
    if (!env.RELAY_KEY || request.headers.get("X-Relay-Key") !== env.RELAY_KEY) {
      return new Response("Forbidden", { status: 403 });
    }

    const url = new URL(request.url);
    if (request.method !== "GET" || !url.pathname.startsWith("/stats/")) {
      return new Response("Not found", { status: 404 });
    }

    const started = Date.now();
    try {
      const upstream = await fetch(UPSTREAM + url.pathname + url.search, {
        headers: NBA_HEADERS,
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      return new Response(upstream.body, {
        status: upstream.status,
        headers: {
          "Content-Type": upstream.headers.get("Content-Type") || "application/json",
          "X-Relay-Upstream-Ms": String(Date.now() - started),
        },
      });
    } catch (err) {
      // Timeout or network error reaching stats.nba.com.
      return new Response(`Upstream error: ${err.name}: ${err.message}`, {
        status: 504,
        headers: { "X-Relay-Upstream-Ms": String(Date.now() - started) },
      });
    }
  },
};
