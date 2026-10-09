"""Explorer-style Windows folder picker, including native folder creation."""
import ctypes
import os
import uuid
from pathlib import Path
from tkinter import filedialog


class _GUID(ctypes.Structure):
    _fields_ = [("data1", ctypes.c_uint32), ("data2", ctypes.c_uint16),
                ("data3", ctypes.c_uint16), ("data4", ctypes.c_ubyte * 8)]

    @classmethod
    def parse(cls, value):
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


def _call(pointer, slot, types=(), *args):
    table = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    method = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *types)(table[slot])
    return method(pointer, *args)


def _check(result):
    if result < 0:
        raise OSError(f"Windows folder picker failed (0x{result & 0xffffffff:08X})")


def _windows_directory(owner, initial):
    ole = ctypes.OleDLL("ole32")
    shell = ctypes.OleDLL("shell32")
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    ole.CoInitializeEx.restype = ctypes.c_long
    ole.CoCreateInstance.argtypes = [ctypes.POINTER(_GUID), ctypes.c_void_p,
                                   ctypes.c_uint32, ctypes.POINTER(_GUID),
                                   ctypes.POINTER(ctypes.c_void_p)]
    ole.CoCreateInstance.restype = ctypes.c_long
    ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    ole.CoTaskMemFree.restype = None
    ole.CoUninitialize.argtypes = []
    ole.CoUninitialize.restype = None
    shell.SHCreateItemFromParsingName.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p,
                                                 ctypes.POINTER(_GUID),
                                                 ctypes.POINTER(ctypes.c_void_p)]
    shell.SHCreateItemFromParsingName.restype = ctypes.c_long
    _check(ole.CoInitializeEx(None, 2))  # UI thread: apartment-threaded COM.
    dialog, result, start, text = (ctypes.c_void_p() for _ in range(4))
    try:
        clsid = _GUID.parse("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")
        iid = _GUID.parse("D57C7288-D4AD-4768-BE02-9D969532D960")
        shell_iid = _GUID.parse("43826D1E-E718-42EE-BC55-A1E261C37BFE")
        _check(ole.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(dialog)))
        options = ctypes.c_uint32()
        _check(_call(dialog, 10, (ctypes.POINTER(ctypes.c_uint32),), ctypes.byref(options)))
        # FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST.
        _check(_call(dialog, 9, (ctypes.c_uint32,), options.value | 0x20 | 0x40 | 0x800))
        _check(_call(dialog, 17, (ctypes.c_wchar_p,), "选择保存目录"))
        _check(_call(dialog, 18, (ctypes.c_wchar_p,), "选择文件夹"))
        folder = Path(initial).expanduser() if initial else Path.home()
        while not folder.is_dir() and folder != folder.parent:
            folder = folder.parent
        if folder.is_dir():
            _check(shell.SHCreateItemFromParsingName(str(folder.resolve()), None,
                                                     ctypes.byref(shell_iid), ctypes.byref(start)))
            # Reopen the selected destination; otherwise allow Windows to remember its location.
            _check(_call(dialog, 12 if initial else 11, (ctypes.c_void_p,), start))
        shown = _call(dialog, 3, (ctypes.c_void_p,), owner)
        if shown & 0xffffffff == 0x800704C7:  # User canceled.
            return None
        _check(shown)
        _check(_call(dialog, 20, (ctypes.POINTER(ctypes.c_void_p),), ctypes.byref(result)))
        _check(_call(result, 5, (ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)),
                     0x80058000, ctypes.byref(text)))  # SIGDN_FILESYSPATH.
        return ctypes.wstring_at(text)
    finally:
        if text:
            ole.CoTaskMemFree(text)
        for pointer in (result, start, dialog):
            if pointer:
                _call(pointer, 2)
        ole.CoUninitialize()


def choose_directory(parent, initial=""):
    """Return an existing folder, or None on cancellation; run on the GUI thread."""
    if os.name != "nt":
        return filedialog.askdirectory(parent=parent, title="选择保存目录",
                                       initialdir=initial or str(Path.home()), mustexist=True)
    parent.update_idletasks()
    user = ctypes.WinDLL("user32")
    user.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    user.GetAncestor.restype = ctypes.c_void_p
    owner = user.GetAncestor(parent.winfo_id(), 2)  # Tk wrapper HWND, GA_ROOT.
    return _windows_directory(owner, initial)
