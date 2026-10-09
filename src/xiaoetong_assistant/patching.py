"""Version-scoped ASAR bootstrap patch with backup and guarded restoration."""
import copy
import csv
import hashlib
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path

SUPPORTED_VERSION = "1.2.18"
BOOTSTRAP = "out/main/xiaoetong-downloader-bootstrap.cjs"
FUSE_MAGIC = b"dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX"


def require_client_closed():
    if os.name != "nt":
        return
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq 小鹅通学员版.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True, errors="replace", check=True)
    if any(len(row) > 1 and row[1].isdigit() for row in csv.reader(result.stdout.splitlines())):
        raise RuntimeError("Exit the Xiaoetong client from its tray before installing or restoring the patch")


def index_of(archive):
    with Path(archive).open("rb") as stream:
        prefix = stream.read(16)
        if len(prefix) != 16 or struct.unpack_from("<I", prefix, 0)[0] != 4:
            raise ValueError("Invalid ASAR prefix")
        header_size = struct.unpack_from("<I", prefix, 4)[0]
        json_size = struct.unpack_from("<I", prefix, 12)[0]
        if json_size > 32 * 1024 * 1024 or header_size < json_size + 8:
            raise ValueError("Invalid ASAR header")
        return json.loads(stream.read(json_size)), 8 + header_size


def entry(index, name):
    node = index
    for part in name.split("/"):
        node = node["files"][part]
    return node


def read_entry(archive, index, base, name):
    node = entry(index, name)
    if node.get("unpacked") or node["size"] > 1024 * 1024:
        raise ValueError("Unsupported metadata entry")
    with Path(archive).open("rb") as stream:
        stream.seek(base + int(node["offset"]))
        data = stream.read(node["size"])
    if len(data) != node["size"]:
        raise ValueError("Truncated ASAR data")
    return data


def serialize_header(index):
    raw = json.dumps(index, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    padding = b"\0" * ((-len(raw)) % 4)
    pickle = struct.pack("<II", len(raw) + len(padding) + 4, len(raw)) + raw + padding
    return struct.pack("<II", 4, len(pickle)) + pickle


def add_entry(index, name, data, offset):
    # Only tiny new metadata/bootstrap entries are hashed, never the client archive.
    digest = hashlib.sha256(data).hexdigest()
    node = {"size": len(data), "offset": str(offset), "integrity": {
        "algorithm": "SHA256", "hash": digest, "blockSize": 4 * 1024 * 1024, "blocks": [digest],
    }}
    parent = index
    parts = name.split("/")
    for part in parts[:-1]:
        parent = parent["files"].setdefault(part, {"files": {}})
    parent["files"][parts[-1]] = node


def inspect_fuses(executable):
    carry = b""
    with Path(executable).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            data = carry + chunk
            at = data.find(FUSE_MAGIC)
            if at >= 0:
                wire = data[at + len(FUSE_MAGIC):]
                if len(wire) < 12:
                    wire += stream.read(64)
                if wire[0] != 1 or wire[1] < 6:
                    raise ValueError("Unsupported Electron fuse format")
                return {"embedded_asar_integrity": chr(wire[2 + 4]), "only_load_asar": chr(wire[2 + 5])}
            carry = data[-128:]
    raise ValueError("Electron fuse metadata not found")


def prepare(source, target, bridge):
    source, target = Path(source), Path(target)
    if source.resolve() == target.resolve() or target.exists():
        raise FileExistsError("Prepared patch must use a new path")
    index, base = index_of(source)
    package = json.loads(read_entry(source, index, base, "package.json"))
    if package.get("version") != SUPPORTED_VERSION or package.get("main") != "out/main/index.js":
        raise ValueError("Client version or main entry is not supported")
    if not Path(bridge).is_file():
        raise FileNotFoundError("Native bridge source is missing")
    original_data_size = source.stat().st_size - base
    package["main"] = BOOTSTRAP
    package_data = json.dumps(package, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    bootstrap = ("'use strict';\ntry { require(" + json.dumps(str(Path(bridge).resolve())) + "); } catch (_) {}\nrequire('./index.js');\n").encode("utf-8")
    patched = copy.deepcopy(index)
    add_entry(patched, "package.json", package_data, original_data_size)
    add_entry(patched, BOOTSTRAP, bootstrap, original_data_size + len(package_data))
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with source.open("rb") as original, target.open("xb") as output:
            output.write(serialize_header(patched))
            original.seek(base)
            shutil.copyfileobj(original, output, 1024 * 1024)
            output.write(package_data)
            output.write(bootstrap)
            output.flush()
            os.fsync(output.fileno())
        check, new_base = index_of(target)
        if json.loads(read_entry(target, check, new_base, "package.json"))["main"] != BOOTSTRAP:
            raise ValueError("Prepared patch validation failed")
        if read_entry(target, check, new_base, BOOTSTRAP) != bootstrap:
            raise ValueError("Prepared bootstrap validation failed")
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {"version": SUPPORTED_VERSION, "patch": "native_session_bridge", "prepared_bytes": target.stat().st_size}


def install(client, bridge):
    require_client_closed()
    client = Path(client).resolve(strict=True)
    archive = client / "resources" / "app.asar"
    backup = archive.with_name("app.asar.xiaoetong-downloader.bak")
    staged = archive.with_name("app.asar.xiaoetong-downloader.new")
    fuses = inspect_fuses(client / "小鹅通学员版.exe")
    if fuses["embedded_asar_integrity"] != "0":
        raise RuntimeError("Embedded ASAR integrity is enabled or unknown; no binary protection flags are changed")
    if backup.exists() or staged.exists():
        raise FileExistsError("Patch backup or staging file already exists; inspect before modifying")
    result = prepare(archive, staged, bridge)
    # Rename keeps a byte-for-byte original backup; no full-archive hash is needed.
    try:
        archive.rename(backup)
    except Exception:
        staged.unlink(missing_ok=True)
        raise
    try:
        staged.rename(archive)
    except Exception:
        backup.rename(archive)
        raise
    return {**result, "backup": str(backup)}


def restore(client):
    require_client_closed()
    archive = Path(client).resolve(strict=True) / "resources" / "app.asar"
    backup = archive.with_name("app.asar.xiaoetong-downloader.bak")
    index, base = index_of(archive)
    package = json.loads(read_entry(archive, index, base, "package.json"))
    if package.get("main") != BOOTSTRAP or package.get("version") != SUPPORTED_VERSION or not backup.is_file():
        raise ValueError("Installed patch not recognized; no files restored")
    original, old_base = index_of(backup)
    old_package = json.loads(read_entry(backup, original, old_base, "package.json"))
    if old_package.get("main") != "out/main/index.js" or old_package.get("version") != SUPPORTED_VERSION:
        raise ValueError("Backup metadata does not match the supported original")
    previous = archive.with_name("app.asar.xiaoetong-downloader.removed")
    if previous.exists():
        raise FileExistsError("Previous restored patch file already exists")
    archive.rename(previous)
    try:
        backup.rename(archive)
    except Exception:
        previous.rename(archive)
        raise
    previous.unlink()


def rebind(client, bridge):
    """Rebuild the installed bootstrap after moving our project; keep original backup."""
    require_client_closed()
    archive = Path(client).resolve(strict=True) / "resources" / "app.asar"
    backup = archive.with_name("app.asar.xiaoetong-downloader.bak")
    staged = archive.with_name("app.asar.xiaoetong-downloader.new")
    previous = archive.with_name("app.asar.xiaoetong-downloader.previous")
    index, base = index_of(archive)
    package = json.loads(read_entry(archive, index, base, "package.json"))
    if package.get("main") != BOOTSTRAP or package.get("version") != SUPPORTED_VERSION or not backup.is_file():
        raise ValueError("Installed patch not recognized")
    if previous.exists():
        raise FileExistsError("Previous patch staging file already exists")
    result = prepare(backup, staged, bridge)
    try:
        archive.rename(previous)
    except Exception:
        staged.unlink(missing_ok=True)
        raise
    try:
        staged.rename(archive)
    except Exception:
        previous.rename(archive)
        staged.unlink(missing_ok=True)
        raise
    previous.unlink()
    return {**result, "rebound": True}
