# SunXBrowser

Desktop browser built with Electron/Chromium, with Chrome-inspired tabs, address bar, bookmarks, browsing history, downloads and private windows. Windows x64 and macOS Intel / Apple Silicon.

## Download
Open [Releases](https://github.com/jphonda/SunXBrowser/releases). Download the Windows `.exe`, macOS `arm64.dmg` for Apple Silicon, or `x64.dmg` for Intel. These initial preview installers are unsigned, so the operating system can display an installation warning. No paid signing account or paid cloud runner is used.

## Free cloud build
Go to **Actions → Build SunXBrowser installers → Run workflow**. Standard GitHub-hosted runners build the three installers and publish a preview Release after tests pass. The public repository uses free standard runners. No AWS resources are needed. See [CLOUD_BUILD.md](CLOUD_BUILD.md).

## Secure DNS
At startup the app calls Electron `app.configureHostResolver` with built-in resolution, `secureDnsMode: secure` and `https://1.1.1.1/dns-query`. This sets Cloudflare DNS over HTTPS within the app; it does not change system DNS or require OS DNS permission. Strict mode intentionally fails if the encrypted resolver is unavailable, instead of falling back to unencrypted DNS. Localhost and IP literals do not require DNS. Website camera/location permissions remain separate and require approval.

## Develop
```
cd electron
npm ci
npm test
npm run smoke
npm start
```
`npm run dist -- --win --x64` on Windows; `npm run dist -- --mac --arm64` or `--x64` on macOS. The cloud workflow supplies matching native hosts.

The UI resembles Chrome, but this is an independent Electron browser: Chrome extensions, Google account sync and full Chrome feature parity are not included. It uses the project's existing S logo.

The older full Chromium source overlay under `SunXBrowser/` is retained as legacy reference only. Current installers are built from `electron/` and do not invoke paid self-hosted runners.
