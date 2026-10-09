import json
import tempfile
import unittest
from pathlib import Path

from xiaoetong_assistant.patching import BOOTSTRAP, index_of, prepare, read_entry, serialize_header


class PatchingTests(unittest.TestCase):
    def fixture(self, root, version="1.2.18"):
        metadata = json.dumps({"main": "out/main/index.js", "version": version}).encode()
        main = b"module.exports = 42;"
        index = {"files": {"package.json": {"size": len(metadata), "offset": "0"}, "out": {"files": {"main": {"files": {"index.js": {"size": len(main), "offset": str(len(metadata))}}}}}}}
        source = root / "original.asar"
        source.write_bytes(serialize_header(index) + metadata + main)
        bridge = root / "bridge.cjs"
        bridge.write_text("module.exports = {};", encoding="utf-8")
        return source, bridge, main

    def test_prepared_archive_preserves_original_entry_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, bridge, main = self.fixture(root)
            original = source.read_bytes()
            target = root / "prepared.asar"
            prepare(source, target, bridge)
            index, base = index_of(target)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(read_entry(target, index, base, "out/main/index.js"), main)
            self.assertEqual(json.loads(read_entry(target, index, base, "package.json"))["main"], BOOTSTRAP)
            self.assertIn(b"require('./index.js')", read_entry(target, index, base, BOOTSTRAP))

    def test_unknown_version_does_not_produce_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, bridge, _ = self.fixture(root, "9.9.9")
            target = root / "prepared.asar"
            with self.assertRaises(ValueError):
                prepare(source, target, bridge)
            self.assertFalse(target.exists())

    def test_existing_destination_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, bridge, _ = self.fixture(root)
            target = root / "prepared.asar"
            target.write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                prepare(source, target, bridge)
            self.assertEqual(target.read_bytes(), b"existing")


    def test_move_rebind_preserves_original_backup_and_restoration(self):
        from unittest.mock import patch
        from xiaoetong_assistant.patching import rebind, restore
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, bridge, main = self.fixture(root)
            resources = root / "resources"
            resources.mkdir()
            original = source.read_bytes()
            backup = resources / "app.asar.xiaoetong-downloader.bak"
            source.rename(backup)
            archive = resources / "app.asar"
            prepare(backup, archive, bridge)
            moved = root / "moved-bridge.cjs"
            moved.write_text("module.exports = {};", encoding="utf8")
            with patch("xiaoetong_assistant.patching.require_client_closed"):
                rebind(root, moved)
                self.assertEqual(backup.read_bytes(), original)
                index, base = index_of(archive)
                self.assertIn(str(moved).replace("\\", "\\\\").encode(), read_entry(archive, index, base, BOOTSTRAP))
                restore(root)
                self.assertEqual(archive.read_bytes(), original)
