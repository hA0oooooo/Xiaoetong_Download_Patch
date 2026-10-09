"""One shared resource download path for GUI and CLI."""
from urllib.parse import urlparse

from .downloads import safe_name, download_file
from .media import download_hls, select_stream, inspect_mp4
from .documents import document_format, download_document


def download_resource(client, item, destination, cancel, progress=lambda *_: None):
    if not item.unlocked or item.trial:
        raise PermissionError("Resource is locked or trial-only")
    folder = destination / safe_name(item.course_title)
    if item.resource_type == 3:
        name = safe_name(item.title)
        if name.lower().endswith(".mp4"):
            name = name[:-4]
        file = folder / (name + ".mp4")
        if file.exists():
            raise FileExistsError("Destination already exists")
        data = client.video(**item.video_identity())
        stream = select_stream(data)
        quality = str(stream.get("definition_p") or "最高可用画质")
        def report(done, total, size):
            progress(f"{quality} · {done / total:.0%}")
        if urlparse(stream["url"]).path.lower().endswith(".mp4"):
            def report_file(done, total):
                progress(f"{quality} · {done / total:.0%}" if total else f"{quality} · {done / 1048576:.1f} MB")
            download_file(stream["url"], file, cancel, report_file, validate=inspect_mp4)
            return file, {"definition": quality, **inspect_mp4(file)}
        return file, download_hls(data, file, cancel, report)
    if item.resource_type == 51:
        info = client.document(**item.video_identity())
        extension = document_format(info)
        name = safe_name(item.title)
        if name.lower().endswith("." + extension):
            name = name[:-(len(extension) + 1)]
        file = folder / (name + "." + extension)
        def report(done, total):
            progress(f"{done / total:.0%}" if total else f"{done / 1048576:.1f} MB")
        download_document(info, file, cancel, report)
        return file, {"format": extension}
    raise ValueError("Unsupported resource type")
