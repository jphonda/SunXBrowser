import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package = load("package")
ci = load("ci_build")


class RuntimePayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.src = Path(self.temp.name) / "src"
        self.out = self.src / "out/SunXBrowser"
        self.stage = Path(self.temp.name) / "payload"
        self.stage.mkdir()
        self.out.mkdir(parents=True)
        (self.src / "LICENSE").write_text("license fixture")
        self.files = ["chrome.exe", "chrome.dll", "resources.pak", "icudtl.dat", "locales/en-US.pak"]
        for name in self.files:
            file = self.out / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"unit test fixture, not browser binary")

    def test_exact_runtime_payload_and_license(self):
        (self.out / "obj").mkdir()
        (self.out / "obj/unused.obj").write_bytes(b"must not ship")
        package.stage_windows(self.src, self.out, self.stage, self.files + [""])
        self.assertTrue((self.stage / "locales/en-US.pak").is_file())
        self.assertTrue((self.stage / "LICENSE.txt").is_file())
        self.assertFalse((self.stage / "obj").exists())

    def test_missing_critical_runtime_fails(self):
        with self.assertRaisesRegex(RuntimeError, "Incomplete runtime"):
            package.stage_windows(self.src, self.out, self.stage, ["chrome.exe"])

    def test_parent_path_and_root_fail(self):
        for dep in ("../../LICENSE", "."):
            with self.subTest(dep=dep), self.assertRaisesRegex(RuntimeError, "outside build"):
                package.stage_windows(self.src, self.out, self.stage, [dep])

    def test_deletion_manifest_preserves_unknown_files_and_profiles(self):
        package.stage_windows(self.src, self.out, self.stage, self.files)
        manifest = package.deletion_manifest(self.stage)
        self.assertIn('Delete "$INSTDIR\\locales\\en-US.pak"', manifest)
        self.assertIn('RMDir "$INSTDIR\\locales"', manifest)
        self.assertNotIn("RMDir /r", manifest)
        self.assertNotIn("LOCALAPPDATA", manifest)
        self.assertNotIn("*", manifest)

    def test_version_requires_all_four_fields(self):
        (self.src / "chrome").mkdir()
        (self.src / "chrome/VERSION").write_text("MAJOR=154\nMINOR=0\nBUILD=8000\nPATCH=1\n")
        self.assertEqual(package.version(self.src), "154.0.8000.1")


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dist = self.root / "dist"
        self.dist.mkdir()
        self.work = self.root / "sunx-123-1-x64"
        self.work.mkdir()
        self.state = {"work": str(self.work), "run_id": "123", "attempt": "1", "cpu": "x64"}
        (self.dist / "ci-state.json").write_text(json.dumps(self.state))
        (self.work / ".sunx-ci-owner.json").write_text(json.dumps(self.state))

    def test_removes_only_owned_run(self):
        unrelated = self.root / "other-checkout"
        unrelated.mkdir()
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}):
            ci.cleanup(self.dist)
        self.assertFalse(self.work.exists())
        self.assertTrue(unrelated.exists())

    def test_other_run_is_never_removed(self):
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "999", "GITHUB_RUN_ATTEMPT": "1"}):
            with self.assertRaisesRegex(RuntimeError, "not owned"):
                ci.cleanup(self.dist)
        self.assertTrue(self.work.exists())

    def test_mismatched_marker_is_never_removed(self):
        (self.work / ".sunx-ci-owner.json").write_text("{}")
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}):
            with self.assertRaisesRegex(RuntimeError, "not owned"):
                ci.cleanup(self.dist)
        self.assertTrue(self.work.exists())


class PreflightTests(unittest.TestCase):
    def test_low_disk_space_stops_before_download(self):
        with tempfile.TemporaryDirectory() as temp:
            disk = type("Disk", (), {"free": 14 * 1024**3})()
            with patch.object(ci.platform, "system", return_value="Windows"), patch.object(ci.platform, "machine", return_value="AMD64"), patch.object(ci.shutil, "disk_usage", return_value=disk):
                with self.assertRaisesRegex(RuntimeError, "200 GiB"):
                    ci.preflight(Path(temp), "x64")

    def test_wrong_native_architecture_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(ci.platform, "system", return_value="Darwin"), patch.object(ci.platform, "machine", return_value="x86_64"):
                with self.assertRaisesRegex(RuntimeError, "ARM64 runner"):
                    ci.preflight(Path(temp), "arm64")


if __name__ == "__main__":
    unittest.main()
