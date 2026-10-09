# Web Import

Bayanat can import media directly from a public URL. Paste a link to a video or audio post and Bayanat downloads it in the background (using [yt-dlp](https://github.com/yt-dlp/yt-dlp)) and attaches it to a new Bulletin.

This is distinct from [Data Import](/guide/data-import), which loads spreadsheets in bulk.

## Supported Sources

Hundreds of sites are supported, including YouTube, Twitter/X, Facebook, and Telegram. See yt-dlp's [supported sites list](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

## JavaScript Runtime

YouTube serves media behind a JavaScript challenge, which yt-dlp solves with a JavaScript runtime. Since v5.1.3, Bayanat ships the runtime (Deno) and yt-dlp's challenge solver with its Python dependencies, so there is nothing to install.

On hardened installer-managed installs, run `sudo bayanat harden --force` once after updating to v5.1.3 or later. It applies the worker setting Deno needs to start; `bayanat status` shows `Units: out of date` until you do.

Manual installs get both through `uv sync --frozen`. If your own Celery service unit sets `SystemCallFilter=@system-service`, also allow `pkey_alloc pkey_free pkey_mprotect`, or Deno is stopped at startup.

::: tip Keep Bayanat current
Large platforms change their extraction logic, and an outdated yt-dlp can make imports that used to work start failing. A Bayanat release can update the yt-dlp version it ships, so check for a newer Bayanat release first.
:::

## Enabling Web Import

Web import is configured under **System Administration → Web import**. Toggle it on to reveal three settings:

| Setting | Purpose |
|---------|---------|
| Web import proxy | Route downloads through a proxy. Leave blank for a direct connection. |
| Allowed domains | A safety list of domains media may be imported from. URLs outside this list are rejected. |
| Web import cookies | Login cookies for sites that require authentication. Stored as a secret and masked after saving. |

::: tip Changes apply on save
Saving the form reloads Bayanat automatically (a brief "Restarting..." screen appears and clears within a minute). No manual restart is needed.
:::

## Proxy

A proxy routes downloads through a different network, which helps when a source is geo-blocked or rate-limiting your server's IP. The value is a single address in the form `scheme://host:port`. A port is always required.

Supported schemes: `http`, `https`, `socks4`, `socks5`, `socks5h`. Add credentials in front of the host if needed:

```
socks5h://username:password@proxy.example.com:1080
```

### Easiest option: a local Tor relay

Installing Tor on the Bayanat server gives you a working SOCKS proxy with no account or extra configuration. The package starts a background service that listens on port `9050` automatically.

```bash
sudo apt update && sudo apt install -y tor
```

Then set the proxy to:

```
socks5h://127.0.0.1:9050
```

::: tip socks5 vs socks5h
Prefer `socks5h://` for Tor: the proxy resolves the destination hostname, rather than your server doing the lookup first.
:::

::: warning SOCKS and downloads that need ffmpeg
Downloads handled by yt-dlp itself, including regular HLS streams, use the proxy. Some are handed to ffmpeg instead: live streams, some encrypted streams, and clipped sections of a video. ffmpeg cannot use a SOCKS proxy, and yt-dlp warns that these downloads are likely to fail. If you need them, use an HTTP proxy (for example Privoxy in front of Tor). If every connection must go through the proxy, also block direct outbound traffic from the worker with a firewall.
:::

::: warning
Tor exit nodes are themselves often blocked by large platforms (YouTube may show CAPTCHAs), and Tor is slower than a direct connection. It is excellent for censored or geo-blocked material and for hiding the server's IP, but it is not a universal fix. A commercial residential proxy is the alternative when a platform blocks Tor.
:::

### Routing all downloads through Tor

Install Privoxy and point it at the Tor relay. Add these lines to `/etc/privoxy/config`:

```
listen-address 127.0.0.1:8118
forward-socks5t / 127.0.0.1:9050 .
toggle 0
```

The trailing dot on the `forward-socks5t` line is required. `toggle 0` turns off Privoxy's content filtering so media reaches Bayanat unchanged.

Then set **Web import proxy** to `http://127.0.0.1:8118`. yt-dlp passes this to ffmpeg as `http_proxy`, and ffmpeg ignores SOCKS.

An administrator can change the app setting, so enforce the route in the firewall too. This nftables rule set lets the Celery worker reach only loopback and the storage endpoint, and drops everything else. Tor and Privoxy run under their own users and are not affected.

```nft
table inet bayanat_egress {
    set storage_v4 { type ipv4_addr; elements = { 203.0.113.10 } }
    set storage_v6 { type ipv6_addr; elements = { 2001:db8::10 } }
    chain output {
        type filter hook output priority 0; policy accept;
        meta skuid "bayanat-celery" oifname "lo" accept
        meta skuid "bayanat-celery" ip daddr @storage_v4 accept
        meta skuid "bayanat-celery" ip6 daddr @storage_v6 accept
        meta skuid "bayanat-celery" drop
    }
}
```

The table is `inet`, so the final drop applies to IPv6 as well as IPv4. Replace the sample addresses with your storage endpoint. Add the database and Redis addresses if they are not on loopback, and make sure name resolution works from loopback (for example through a local stub resolver).

## Cookies

Some media is private, age-restricted, or members-only, and the source serves it only to a logged-in session. Providing cookies lets Bayanat download as if it were that logged-in browser. Bayanat first tries without cookies and only retries with them if the download is rejected for authentication.

::: warning Use a throwaway account
Cookies grant access to whatever account they came from. Always export them from a dedicated, disposable archiving account, never a personal or organisational primary account.
:::

Cookies must be in **Netscape format** (the classic `cookies.txt` layout, tab-separated). To export them:

1. Open a private or incognito window and sign in to the source site with the archiving account. Keep this the only private tab open.
2. For YouTube, which rotates the cookies of open sessions, go to `https://www.youtube.com/robots.txt` in the same tab before exporting.
3. Export the cookies for that site only, for example with the open-source [Get cookies.txt LOCALLY](https://github.com/kairi003/Get-cookies.txt-LOCALLY) extension (allow it in private windows). Do not use an "export all" option: that file includes cookies from every other site, which can include login sessions.
4. Close the private window so the session is never used in the browser again, then paste the file contents into the **Web import cookies** field and save.

See yt-dlp's [YouTube cookie guide](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies) for details.

```
# domain        flag  path  secure  expiry      name                value
.youtube.com    TRUE  /     TRUE    1735689600  VISITOR_INFO1_LIVE  CgtadGVzdGluZ...
```

::: tip Cookies expire
The `expiry` column is a date. If logins that worked before start failing, your cookies have likely expired. Log in again, re-export, and paste the fresh values.
:::

## How It Works

1. You submit a URL; Bayanat checks its domain against **Allowed domains**.
2. A background worker downloads the media via yt-dlp, applying the proxy if set.
3. If cookies are configured and the error looks like an authentication problem (sign-in or age checks), it retries using your cookies.
4. When the download finishes you receive a notification, and the media is then imported into a new Bulletin in the background. If the download fails, the notification includes the reason, for example that the site requires sign-in or that the cookies may have expired.

Web import needs `ffmpeg` and `ffprobe` on the server. The installer installs both; if either is missing, imports fail with a message naming it, and `flask doctor` reports it.

## Configuration

See [Configuration](/deployment/configuration) for full setup details.
