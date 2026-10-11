"""Build a pinned Chromium checkout with the SunXBrowser source overlay.

Run with Python 3 on the target OS, with depot_tools on PATH.
This does not install policy, change OS DNS, or request DNS/VPN permissions.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "upstream.json").read_text())


def run(*args, cwd):
    # Windows depot_tools entry points are batch wrappers.
    executable = shutil.which(args[0])
    if not executable:
        raise RuntimeError(f"Missing {args[0]}; add depot_tools to PATH.")
    command = [executable, *map(str, args[1:])]
    if os.name == "nt" and executable.lower().endswith((".bat", ".cmd")):
        command = [os.environ.get("COMSPEC", "cmd.exe"), "/c", *command]
    subprocess.run(command, cwd=cwd, check=True)


def apply_overlay(src):
    patch = ROOT / "patches" / "sunxbrowser.patch"
    # Fail before modifying any file if source context has changed.
    reverse = subprocess.run(
        ["git", "apply", "--reverse", "--check", str(patch)], cwd=src,
        capture_output=True,
    )
    if reverse.returncode != 0:
        run("git", "apply", "--check", patch, cwd=src)
        run("git", "apply", patch, cwd=src)
    assets = ROOT / "assets"
    theme = src / "chrome/app/theme"
    for file in assets.glob("product_logo_*.png"):
        shutil.copy2(file, theme / "chromium" / file.name)
    for scale in (100, 200):
        for size in (16, 32):
            shutil.copy2(
                assets / f"logo-{size * scale // 100}.png",
                theme / f"default_{scale}_percent/chromium/product_logo_{size}.png",
            )
    shutil.copy2(assets / "app.ico", theme / "chromium/win/chromium.ico")
    shutil.copy2(assets / "app.icns", theme / "chromium/mac/app.icns")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, help="Chromium workspace, outside this project")
    parser.add_argument("--fetch", action="store_true", help="Download Chromium and dependencies")
    parser.add_argument("--apply-only", action="store_true")
    parser.add_argument("--target-cpu", choices=("x64", "arm64"))
    args = parser.parse_args()
    host = platform.system()
    if host not in ("Darwin", "Windows"):
        raise RuntimeError("Use macOS for the Mac build or Windows for the Windows build.")
    checkout = args.checkout.expanduser().resolve()
    if " " in str(checkout):
        raise RuntimeError("Chromium checkout path must have no spaces.")
    checkout.mkdir(parents=True, exist_ok=True)
    src = checkout / "src"
    if args.fetch:
        free_gb = shutil.disk_usage(checkout).free / 1024**3
        if free_gb < 150:
            raise RuntimeError(f"Only {free_gb:.1f} GiB free; reserve at least 150 GiB before fetching.")
        if src.exists():
            raise RuntimeError("Checkout already exists; sync it manually to the pinned revision.")
        # Fetch only the pinned revision, rather than fetching main first.
        run("gclient", "config", CONFIG["repository"], "--unmanaged", cwd=checkout)
        src.mkdir()
        run("git", "init", cwd=src)
        run("git", "remote", "add", "origin", CONFIG["repository"], cwd=src)
        run("git", "fetch", "origin", CONFIG["revision"], "--depth=1", cwd=src)
        run("git", "checkout", "--detach", CONFIG["revision"], cwd=src)
        run("gclient", "sync", "-D", "--no-history", cwd=checkout)
    if not (src / ".git").exists():
        raise RuntimeError("No Chromium src checkout. Use --fetch on a disk with sufficient space.")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=src, text=True).strip()
    if revision != CONFIG["revision"]:
        raise RuntimeError(f"Wrong upstream revision: {revision}; expected {CONFIG['revision']}")
    apply_overlay(src)
    if args.apply_only:
        print("Source overlay applied. This is not a compiled browser.")
        return
    build_dir = src / "out/SunXBrowser"
    build_dir.mkdir(parents=True, exist_ok=True)
    cpu_arg = f'target_cpu = "{args.target_cpu}"\n' if args.target_cpu else ""
    (build_dir / "args.gn").write_text(
        'is_debug = false\nis_component_build = false\nsymbol_level = 0\n'
        'is_chrome_branded = false\nuse_remoteexec = false\n' + cpu_arg, encoding="utf-8",
    )
    run("gn", "gen", "out/SunXBrowser", cwd=src)
    run("autoninja", "-C", "out/SunXBrowser", "chrome", cwd=src)
    print(f"Built chrome target in {build_dir}. Run the runtime checks in README before distributing.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Build stopped: {error}", file=sys.stderr)
        sys.exit(1)
