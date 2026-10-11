# Free GitHub Actions builds

Repository: https://github.com/jphonda/SunXBrowser (public).

1. Open Actions → Build SunXBrowser installers.
2. Click Run workflow on main.
3. Wait for all three build jobs and the release job to complete.
4. Open Releases and download `.exe` (Windows), `arm64.dmg` (Apple Silicon), or `x64.dmg` (Intel Mac).

Each build runs URL/DNS policy tests and an Electron smoke test, packages native installers, calculates SHA256 checksums, and publishes a preview release. Smoke screenshots and reports are available in workflow artifacts. GitHub standard public-repository runners are free; this workflow does not use larger runners or AWS. Service limits still apply.

Unsigned preview installers may trigger OS security warnings. Paid code signing/notarization is not configured. The app's automatic DNS configuration does not itself require a permission dialog.
