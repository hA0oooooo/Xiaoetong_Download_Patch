"""Install only into this project's virtual environment."""
import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer is required")
    python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")
    # Use pip's existing network configuration, without defining a project proxy.
    common = [str(python), "-m", "pip", "install", "--timeout", "20", "--retries", "1"]
    if (ROOT / "requirements-lock.txt").exists():
        common += ["-c", str(ROOT / "requirements-lock.txt")]
    subprocess.run([*common, "-r", str(ROOT / "requirements.txt")], cwd=ROOT, check=True)
    packages = Path(subprocess.check_output([str(python), "-X", "utf8", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
                                           text=True, encoding="utf-8").strip())
    # Migrate earlier editable installs; the application itself has no package version.
    if any(packages.glob("xiaoetong_video_downloader-*.dist-info")):
        subprocess.run([str(python), "-m", "pip", "uninstall", "-y", "xiaoetong-video-downloader"],
                       cwd=ROOT, check=True)
    # ASCII escapes also support Chinese project paths on non-UTF-8 Windows locales.
    (packages / "xiaoetong_downloader.pth").write_text(
        "import sys; sys.path.insert(0, " + ascii(str(ROOT / "src")) + ")\n", encoding="ascii")
    print("Ready. Open launch.cmd to start the video downloader.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Setup failed ({type(exc).__name__}). Check Python and pip's network configuration.", file=sys.stderr)
        sys.exit(1)
