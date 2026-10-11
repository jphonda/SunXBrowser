"""Cloud runner entry point. Keep large checkouts away from the local computer."""
import argparse
from collections import deque
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "upstream.json").read_text())


def logged(command, log, cwd=None, env=None, timeout=None):
    with log.open("a", encoding="utf-8") as stream:
        stream.write("\n> " + " ".join(map(str, command)) + "\n")
        stream.flush()
        # Write subprocess output straight to disk; avoid buffering a Chromium
        # build's output in memory. GitHub receives phase updates below.
        result = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode:
        # The full log is uploaded even on failure.
        with log.open(encoding="utf-8", errors="replace") as stream:
            lines = deque(stream, maxlen=80)
        print("".join(lines), flush=True)
        raise RuntimeError(f"Command failed ({result.returncode}): {command[0]}; see build.log")


def preflight(work_root, cpu):
    host = platform.system()
    machine = platform.machine().lower()
    if host not in ("Windows", "Darwin"):
        raise RuntimeError("Runner must be Windows or macOS.")
    if cpu == "arm64" and machine not in ("arm64", "aarch64"):
        raise RuntimeError("Use a native ARM64 runner for this build.")
    if cpu == "x64" and machine not in ("amd64", "x86_64"):
        raise RuntimeError("Use a native X64 runner for this build.")
    work_root.mkdir(parents=True, exist_ok=True)
    if " " in str(work_root):
        raise RuntimeError("SUNX_BUILD_ROOT must be a path without spaces.")
    free_gb = shutil.disk_usage(work_root).free / 1024**3
    if free_gb < 200:
        raise RuntimeError(f"Only {free_gb:.1f} GiB free: cloud builds require at least 200 GiB free.")
    if host == "Windows":
        if not (shutil.which("makensis") or shutil.which("makensis.exe")):
            raise RuntimeError("Install NSIS 3; add its directory to runner PATH.")
        vswhere = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"
        if not vswhere.is_file():
            raise RuntimeError("Visual Studio 2026 C++ tools are required; see CLOUD_BUILD.md.")
        installed = subprocess.check_output([
            str(vswhere), "-latest", "-products", "*", "-version", "[18.0,19.0)",
            "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "Microsoft.VisualStudio.Component.VC.ATLMFC", "-property", "installationPath",
        ], text=True).strip()
        if not installed:
            raise RuntimeError("Missing Visual Studio 2026 C++ and ATL/MFC components.")
    else:
        for tool in ("xcodebuild", "hdiutil", "codesign", "ditto"):
            if not shutil.which(tool):
                raise RuntimeError(f"Missing macOS build tool: {tool}")
        subprocess.run(["xcodebuild", "-version"], check=True)


def smoke(checkout, cpu, dist, env):
    out = checkout / "src/out/SunXBrowser"
    exe = out / ("chrome.exe" if platform.system() == "Windows" else "SunXBrowser.app/Contents/MacOS/SunXBrowser")
    if not exe.is_file():
        raise RuntimeError(f"Browser executable missing: {exe}")
    with tempfile.TemporaryDirectory() as temp:
        command = [str(exe), "--headless", "--disable-gpu", "--no-first-run",
                   "--no-default-browser-check", f"--user-data-dir={temp}",
                   "--dump-dom", "data:text/html,<title>SunXBrowserSmoke</title><p>sunx-smoke-ok</p>"]
        result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=120)
        (dist / "smoke.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
        if result.returncode or "sunx-smoke-ok" not in result.stdout:
            raise RuntimeError("Built browser did not pass headless startup/renderer smoke test.")


def cleanup(dist):
    state_file = dist / "ci-state.json"
    if not state_file.exists():
        return
    state = json.loads(state_file.read_text())
    work = Path(state["work"]).resolve()
    marker = work / ".sunx-ci-owner.json"
    if not marker.exists():
        return
    owner = json.loads(marker.read_text())
    if (owner != state or state["run_id"] != os.environ.get("GITHUB_RUN_ID")
            or state["attempt"] != os.environ.get("GITHUB_RUN_ATTEMPT")):
        raise RuntimeError("Refusing to remove a checkout not owned by this workflow run.")
    if work.name != f"sunx-{state['run_id']}-{state['attempt']}-{state['cpu']}":
        raise RuntimeError("Unexpected checkout directory name.")
    # Git checkouts can contain read-only files on Windows.
    def writable_then_retry(func, path, exc):
        os.chmod(path, 0o700)
        func(path)
    shutil.rmtree(work, onexc=writable_then_retry)
    print(f"Removed this run's cloud checkout: {work}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--cpu", choices=("x64", "arm64"))
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    dist = args.dist.resolve()
    dist.mkdir(parents=True, exist_ok=True)
    if args.cleanup:
        cleanup(dist)
        return
    if not args.work_root or not args.cpu:
        parser.error("--work-root and --cpu are required to build")
    preflight(args.work_root.resolve(), args.cpu)
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if not run_id.isdigit() or not attempt.isdigit():
        raise RuntimeError("This script runs in GitHub Actions; use build.py locally.")
    work = args.work_root.resolve() / f"sunx-{run_id}-{attempt}-{args.cpu}"
    if work.exists():
        raise RuntimeError(f"Work directory already exists: {work}; inspect before retrying.")
    work.mkdir()
    state = {"work": str(work), "run_id": run_id, "attempt": attempt, "cpu": args.cpu}
    (work / ".sunx-ci-owner.json").write_text(json.dumps(state))
    (dist / "ci-state.json").write_text(json.dumps(state))
    log = dist / "build.log"
    env = os.environ.copy()
    env.update({"DEPOT_TOOLS_UPDATE": "0", "DEPOT_TOOLS_WIN_TOOLCHAIN": "0", "PYTHONUTF8": "1"})
    depot = work / "depot_tools"
    print("Downloading pinned depot_tools on the cloud runner…", flush=True)
    logged(["git", "init", str(depot)], log)
    logged(["git", "remote", "add", "origin", "https://chromium.googlesource.com/chromium/tools/depot_tools.git"], log, cwd=depot)
    logged(["git", "fetch", "--depth=1", "origin", CONFIG["depot_tools_revision"]], log, cwd=depot)
    logged(["git", "checkout", "--detach", "FETCH_HEAD"], log, cwd=depot)
    env["PATH"] = str(depot) + os.pathsep + env["PATH"]
    checkout = work / "chromium"
    print("Fetching pinned Chromium and building; full output is saved in build.log…", flush=True)
    logged([sys.executable, str(ROOT / "scripts/build.py"), str(checkout), "--fetch", "--target-cpu", args.cpu], log, env=env)
    print("Testing browser startup and renderer…", flush=True)
    smoke(checkout, args.cpu, dist, env)
    print("Packaging installer…", flush=True)
    logged([sys.executable, str(ROOT / "scripts/package.py"), str(checkout), "--dist", str(dist), "--cpu", args.cpu], log, env=env)
    print("Installer and checksum are ready for artifact upload.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Cloud build stopped: {error}", file=sys.stderr, flush=True)
        sys.exit(1)
