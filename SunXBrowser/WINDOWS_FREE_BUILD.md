# Full Chromium Windows build on free standard runners

Workflow: **Build Chromium SunXBrowser Windows free**. This builds the Chromium source overlay, not Electron.

A measured `windows-2025-vs2026` public standard runner provided D: with 147 GiB free, 4 CPUs, 16 GiB RAM and Visual Studio 2026. Actual capacity can vary: every run requires at least 100 GiB free on D: and fails rather than switching to a paid larger runner. No AWS is used.

Builds use the same upstream pin, S logo and strict Cloudflare Secure DNS defaults as the Mac Chromium version. The NSIS installer is per-user and unsigned.

Start the workflow on main with empty `resume_run_id`, `part=1`. Compilation runs with three jobs. Before the six-hour runner limit, incomplete compilation creates a one-day output checkpoint and starts the next standard free runner. Up to three parts continue automatically. Only compile output is checkpointed; Microsoft toolchains are not redistributed. The workflow uses no paid cache expansion. Capacity, transient network failures and compiler errors can still stop a build; diagnostics are uploaded.

Successful builds test the browser, produce the `.exe`, silently install it in the temporary runner, and test the installed executable. Only then is a preview GitHub Release published with installer and SHA256 checksum. An intermediate checkpoint run is not a completed installer.
