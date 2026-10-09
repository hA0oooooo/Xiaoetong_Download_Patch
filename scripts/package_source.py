"""Produce a source-only release without profiles, downloads or vendor files."""
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "runtime", "downloads", "dist", "build", "__pycache__", ".pytest_cache"}
ALLOWED_ROOTS = {"src", "tests", "scripts", ".gitignore", ".gitattributes", "README.md", "LICENSE", "requirements.txt", "requirements-lock.txt", "launch.cmd", "run-tests.cmd"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("Release path already exists; use a new output path")
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    for file in sorted(ROOT.rglob("*")):
        relative = file.relative_to(ROOT)
        if relative.parts[0] not in ALLOWED_ROOTS or not file.is_file() or file.is_symlink() or any(part in EXCLUDED or part.endswith(".egg-info") or part.startswith(".env") for part in relative.parts):
            continue
        if file.resolve() == output or file.suffix.lower() in {".pyc", ".p12", ".pfx", ".pem", ".key", ".bundle", ".sqlite", ".db", ".bak", ".dll", ".exe", ".asar", ".log", ".part"}:
            continue
        entries.append((file, relative))
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for file, relative in entries:
            archive.write(file, Path("xiaoetong-video-downloader") / relative)
    with ZipFile(output) as archive:
        if archive.testzip():
            raise RuntimeError("Archive integrity verification failed")
    print(f"Created source release: {output} ({len(entries)} files)")


if __name__ == "__main__":
    main()
