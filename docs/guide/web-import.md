# Web Import

Bayanat can import media directly from a public URL. Paste a link to a video or audio post and Bayanat downloads it in the background (using [yt-dlp](https://github.com/yt-dlp/yt-dlp)) and attaches it to a new Bulletin.

This is distinct from [Data Import](/guide/data-import), which loads spreadsheets in bulk.

## Supported Sources

Hundreds of sites are supported, including YouTube, Twitter/X, Facebook, and Telegram. See yt-dlp's [supported sites list](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

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

::: warning
Tor exit nodes are themselves often blocked by large platforms (YouTube may show CAPTCHAs), and Tor is slower than a direct connection. It is excellent for censored or geo-blocked material and for hiding the server's IP, but it is not a universal fix. A commercial residential proxy is the alternative when a platform blocks Tor.
:::

## Cookies

Some media is private, age-restricted, or members-only, and the source serves it only to a logged-in session. Providing cookies lets Bayanat download as if it were that logged-in browser. Bayanat first tries without cookies and only retries with them if the download is rejected for authentication.

::: warning Use a throwaway account
Cookies grant access to whatever account they came from. Always export them from a dedicated, disposable archiving account, never a personal or organisational primary account.
:::

Cookies must be in **Netscape format** (the classic `cookies.txt` layout, tab-separated). Export them with a "Get cookies.txt" browser extension while logged in to the source site, then paste the file contents into the **Web import cookies** field.

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
3. If the download is rejected for authentication, it retries using your cookies.
4. On success the media is stored and attached to a new Bulletin, and you receive a notification.

## Configuration

See [Configuration](/deployment/configuration) for full setup details.
