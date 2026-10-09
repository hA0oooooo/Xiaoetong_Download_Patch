"""Streaming file downloads with validators, cancellation and safe resume."""
import json
import hashlib
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from .network import make_session


class DownloadPaused(Exception):
    pass


def safe_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(name)).strip(" .")[:150]
    if not name:
        name = "video"
    if name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        name = "_" + name
    return name


def download_file(url, destination, cancel, progress, session=None, validate=None):
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username:
        raise ValueError("下载地址必须是 HTTP(S) 文件地址")
    if parsed.path.lower().endswith((".m3u8", ".mpd")):
        raise ValueError("不接受播放器清单或 DRM 资源")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError("目标文件已存在，请更改文件名，避免覆盖")
    partial = destination.with_name(destination.name + ".part")
    metadata_path = destination.with_name(destination.name + ".part.json")
    metadata = {}
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if not isinstance(metadata, dict):
                metadata = {}
        except (ValueError, OSError):
            pass
    offset = partial.stat().st_size if partial.exists() else 0
    source_id = hashlib.sha256(url.encode("utf-8")).hexdigest()
    # Never append without a strong validator and a known final size.
    validator = metadata.get("etag")
    expected_total = metadata.get("total")
    if not isinstance(validator, str) or validator.startswith("W/") or not isinstance(expected_total, int) or expected_total <= 0 or offset >= expected_total or metadata.get("source_id") != source_id:
        offset = 0
    headers = {"Accept-Encoding": "identity"}
    if offset:
        headers.update({"Range": f"bytes={offset}-", "If-Range": validator})
    own_session = session is None
    client = session or make_session()
    try:
        with client.get(url, headers=headers, stream=True, timeout=(15, 30)) as response:
            if response.status_code in (401, 403):
                raise PermissionError("登录或下载授权已失效，请重新获取官方导出地址")
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
            if content_type in {"text/html", "application/json", "application/dash+xml", "application/vnd.apple.mpegurl", "application/x-mpegurl"}:
                raise ValueError("服务器返回页面、JSON 或播放清单，并非可下载文件")
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise ValueError("服务器返回压缩传输，不能安全计算断点位置")
            append = False
            if response.status_code == 206:
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                if not match or int(match[1]) != offset:
                    raise ValueError("服务器返回了错误的断点位置")
                total = int(match[3])
                if offset and (response.headers.get("ETag") != validator or total != metadata.get("total")):
                    raise ValueError("源文件已变化，拒绝拼接；请删除该任务的 .part 文件后重试")
                append = bool(offset)
            elif response.status_code == 200:
                offset = 0
                total = int(response.headers.get("Content-Length") or 0)
            else:
                raise ValueError(f"不支持的下载响应：HTTP {response.status_code}")
            metadata_path.write_text(json.dumps({"etag": response.headers.get("ETag"), "total": total, "source_id": source_id}), encoding="utf-8")
            written = offset
            last_event = 0.0
            with partial.open("ab" if append else "wb") as output:
                for chunk in response.iter_content(chunk_size=256 * 1024):
                    if cancel.is_set():
                        raise DownloadPaused()
                    if not chunk:
                        continue
                    # HLS playlists returned with a misleading MIME type must not be saved as video.
                    if written == 0 and (chunk.lstrip().startswith(b"#EXTM3U") or chunk.lstrip().lower().startswith((b"<!doctype html", b"<html"))):
                        raise ValueError("响应实际是播放清单或登录页")
                    output.write(chunk)
                    written += len(chunk)
                    now = time.monotonic()
                    if now - last_event > 0.2:
                        progress(written, total)
                        last_event = now
                output.flush()
                os.fsync(output.fileno())
            if cancel.is_set():
                raise DownloadPaused()
            if total and written != total:
                raise ValueError("文件未完整接收，保留断点供重试")
            if written == 0:
                raise ValueError("服务器返回空文件")
            if validate is not None:
                try:
                    validate(partial)
                except Exception:
                    partial.unlink(missing_ok=True)
                    metadata_path.unlink(missing_ok=True)
                    raise
            if destination.exists():
                raise FileExistsError("下载期间目标文件已出现，拒绝覆盖")
            # Windows rename refuses an existing destination.
            partial.rename(destination)
            metadata_path.unlink(missing_ok=True)
            progress(written, total)
            return destination
    finally:
        if own_session:
            client.close()
