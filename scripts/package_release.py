"""Build a reproducible source distribution from an explicit allowlist."""
import hashlib
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from foundry import __version__
from foundry.project import CORE


def build(destination):
    destination.mkdir(exist_ok=True, parents=True)
    name = f"agent-foundry-{__version__}"
    archive = destination / (name + ".zip")
    with ZipFile(archive.with_suffix(".tmp"), "w") as output:
        for item in sorted((*CORE, "extensions", "templates", "examples", "scripts", "tests", "README.md")):
            path = ROOT / item
            for file in sorted(path.rglob("*") if path.is_dir() else [path]):
                if not file.is_file() or file.is_symlink() or any(
                    part in {"__pycache__", ".runs", ".venv", ".git", ".env"} for part in file.relative_to(ROOT).parts
                ) or file.suffix == ".pyc":
                    continue
                header = ZipInfo(f"{name}/{file.relative_to(ROOT).as_posix()}")
                header.external_attr = 0o100644 << 16
                output.writestr(header, file.read_bytes(), compress_type=ZIP_DEFLATED)
    archive.with_suffix(".tmp").replace(archive)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".sha256").write_text(f"{checksum}  {archive.name}\n")
    return archive


if __name__ == "__main__":
    print(build(ROOT / "dist"))
