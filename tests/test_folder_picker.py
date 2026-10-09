import os
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from xiaoetong_assistant.app import Application
from xiaoetong_assistant import folder_picker


class FolderPickerTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = Application(self.root, connect=False)

    def tearDown(self):
        self.app.close()

    def test_cancel_preserves_destination_and_checked_resources(self):
        self.app.folder.set(str(Path.home()))
        self.app.checked.add("selected-resource")
        with patch("xiaoetong_assistant.app.choose_directory", return_value=None):
            self.app.choose_folder()
        self.assertEqual(self.app.folder.get(), str(Path.home()))
        self.assertEqual(self.app.checked, {"selected-resource"})

    def test_selected_new_folder_becomes_destination_and_enables_download(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "新建课程目录"
            destination.mkdir()
            self.app.checked.add("selected-resource")
            with patch("xiaoetong_assistant.app.choose_directory", return_value=str(destination)):
                self.app.choose_folder()
            self.assertEqual(Path(self.app.folder.get()), destination)
            self.assertNotIn("disabled", self.app.button.state())

    def test_dialog_error_is_visible_and_preserves_destination(self):
        self.app.folder.set(str(Path.home()))
        with patch("xiaoetong_assistant.app.choose_directory", side_effect=OSError()), \
                patch("xiaoetong_assistant.app.messagebox.showerror") as show_error:
            self.app.choose_folder()
        show_error.assert_called_once()
        self.assertEqual(self.app.folder.get(), str(Path.home()))

    @unittest.skipUnless(os.name == "nt", "Requires Windows Shell COM")
    def test_native_configuration_and_unicode_path_conversion(self):
        # Exercise real COM objects and Shell paths without opening a modal UI in CI.
        # Only Show and GetResult are substituted: return the actual configured folder.
        original = folder_picker._call
        def call(pointer, slot, types=(), *args):
            if slot == 3:
                return 0
            return original(pointer, 13 if slot == 20 else slot, types, *args)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "新建课程目录"
            destination.mkdir()
            with patch.object(folder_picker, "_call", side_effect=call):
                self.assertEqual(Path(folder_picker.choose_directory(self.root, str(destination))), destination)
