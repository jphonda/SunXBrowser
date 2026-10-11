"""Create unsigned development installers from an actual Chromium build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def version(src):
    fields = dict(line.split("=", 1) for line in (src / "chrome/VERSION").read_text().splitlines() if "=" in line)
    return ".".join(fields[key] for key in ("MAJOR", "MINOR", "BUILD", "PATCH"))


def stage_windows(src, out, stage, deps):
    for name in deps:
        if not name.strip():
            continue
        path = (out / name.strip()).resolve()
        if path == out.resolve() or not path.is_relative_to(out.resolve()):
            raise RuntimeError(f"Unexpected runtime dependency outside build directory: {name}")
        if not path.exists():
            raise RuntimeError(f"Runtime dependency missing: {name}")
        dest = stage / path.relative_to(out.resolve())
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            for child in path.rglob("*"):
                if not child.resolve().is_relative_to(out.resolve()):
                    raise RuntimeError(f"Dependency symlink escapes build directory: {child}")
            shutil.copytree(path, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(path, dest)
    for required in ("chrome.exe", "chrome.dll", "resources.pak", "icudtl.dat", "locales/en-US.pak"):
        if not (stage / required).is_file():
            raise RuntimeError(f"Incomplete runtime payload: {required}")
    shutil.copy2(src / "LICENSE", stage / "LICENSE.txt")


def nsis_escape(value):
    return str(value).replace("$", "$$").replace('"', '$\\"')


def deletion_manifest(stage):
    lines = []
    for file in sorted(stage.rglob("*")):
        if file.is_file():
            rel = nsis_escape(str(file.relative_to(stage)).replace("/", "\\"))
            lines.append(f'Delete "$INSTDIR\\{rel}"')
    dirs = [p for p in stage.rglob("*") if p.is_dir()]
    for directory in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        rel = nsis_escape(str(directory.relative_to(stage)).replace("/", "\\"))
        lines.append(f'RMDir "$INSTDIR\\{rel}"')
    return "\n".join(lines) + "\n"


def package_windows(src, out, dist, cpu):
    tool = shutil.which("makensis") or shutil.which("makensis.exe")
    if not tool:
        raise RuntimeError("Install NSIS 3 and add makensis.exe to PATH on the Windows runner.")
    gn = shutil.which("gn")
    if not gn:
        raise RuntimeError("gn is not on PATH; run packaging with depot_tools available.")
    command = [gn, "desc", str(out), "//chrome", "runtime_deps"]
    if os.name == "nt" and gn.lower().endswith((".bat", ".cmd")):
        command = [os.environ.get("COMSPEC", "cmd.exe"), "/c", *command]
    deps = subprocess.check_output(command, cwd=src, text=True).splitlines()
    installer = dist / f"SunXBrowser-{version(src)}-windows-{cpu}-unsigned-setup.exe"
    with tempfile.TemporaryDirectory(dir=dist) as temp:
        stage = Path(temp) / "payload"
        stage.mkdir()
        stage_windows(src, out, stage, deps)
        delete_file = Path(temp) / "payload-delete.nsh"
        delete_file.write_text(deletion_manifest(stage), encoding="utf-8")
        subprocess.run([
            tool, "/V3", f"/DPAYLOAD={stage}", f"/DOUTPUT={installer}",
            f"/DVERSION={version(src)}", f"/DPAYLOAD_DELETE={delete_file}",
            str(ROOT / "installer/windows.nsi"),
        ], cwd=ROOT / "installer", check=True)
    return installer


def package_macos(src, out, dist, cpu):
    app = out / "SunXBrowser.app"
    if not app.is_dir():
        raise RuntimeError(f"Expected branded application: {app}")
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    if info.get("CFBundleIdentifier") != "app.sunxbrowser.browser":
        raise RuntimeError("Bundle ID does not match SunXBrowser.")
    # Preserve Chromium's development signing; no mutation of the bundle here.
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    installer = dist / f"SunXBrowser-{version(src)}-macos-{cpu}-unsigned.dmg"
    with tempfile.TemporaryDirectory(dir=dist) as temp:
        image = Path(temp) / "image"
        image.mkdir()
        subprocess.run(["ditto", str(app), str(image / app.name)], check=True)
        (image / "Applications").symlink_to("/Applications")
        shutil.copy2(src / "LICENSE", image / "LICENSE.txt")
        subprocess.run(["hdiutil", "create", "-volname", "SunXBrowser", "-srcfolder", str(image), "-format", "UDZO", str(installer)], check=True)
        subprocess.run(["hdiutil", "verify", str(installer)], check=True)
    return installer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--cpu", choices=("x64", "arm64"), required=True)
    args = parser.parse_args()
    src = args.checkout.resolve() / "src"
    out = src / "out/SunXBrowser"
    dist = args.dist.resolve()
    dist.mkdir(parents=True, exist_ok=True)
    host = platform.system()
    if host == "Windows":
        installer = package_windows(src, out, dist, args.cpu)
    elif host == "Darwin":
        installer = package_macos(src, out, dist, args.cpu)
    else:
        raise RuntimeError("Packaging must run on Windows or macOS.")
    if not installer.is_file() or installer.stat().st_size == 0:
        raise RuntimeError("Installer was not generated.")
    with installer.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    (dist / f"{installer.name}.sha256").write_text(f"{digest}  {installer.name}\n")
    metadata = json.loads((ROOT / "upstream.json").read_text())
    metadata.update({"version": version(src), "os": host, "cpu": args.cpu,
                     "installer": installer.name, "sha256": digest,
                     "status": "installer packaged; see smoke.log for runtime validation",
                     "signing": "development only; no trusted publisher signing/notarization"})
    (dist / "build-info.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Installer: {installer}")


if __name__ == "__main__":
    main()
