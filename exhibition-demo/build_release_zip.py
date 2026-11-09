"""Build a clean laptop-ready ZIP without virtualenvs, caches, or local logs."""
from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

SOURCE = Path(__file__).resolve().parent
OUTPUT = SOURCE.parent / "QSHIFT_Exhibition_Website_FINAL.zip"
ARCHIVE_ROOT = "QSHIFT_Exhibition_Website"
EXCLUDED_PARTS = {".venv", "__pycache__", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log"}


def include(path: Path) -> bool:
    relative = path.relative_to(SOURCE)
    return not any(part in EXCLUDED_PARTS for part in relative.parts) and path.suffix.lower() not in EXCLUDED_SUFFIXES


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"Refusing to overwrite existing release archive: {OUTPUT}")
    files = sorted(path for path in SOURCE.rglob("*") if path.is_file() and include(path))
    required = {
        "README.md",
        "requirements.txt",
        "requirements-test.txt",
        "START_WINDOWS.bat",
        "server.py",
        "index.html",
        "TEST_RESULTS.md",
        "build_release_zip.py",
        "tests/test_demo.py",
        "tests/conftest.py",
    }
    actual = {path.relative_to(SOURCE).as_posix() for path in files}
    missing = required - actual
    if missing:
        raise SystemExit(f"Required release files are missing: {sorted(missing)}")

    with ZipFile(OUTPUT, "x", compression=ZIP_DEFLATED, compresslevel=8) as archive:
        for path in files:
            relative = path.relative_to(SOURCE).as_posix()
            archive.write(path, f"{ARCHIVE_ROOT}/{relative}")
    with ZipFile(OUTPUT, "r") as archive:
        bad = archive.testzip()
        if bad is not None:
            raise SystemExit(f"ZIP integrity check failed at {bad}")
        names = archive.namelist()
        if any(any(part in EXCLUDED_PARTS for part in Path(name).parts) for name in names):
            raise SystemExit("Release ZIP unexpectedly contains a virtual environment or cache")
        if any(name.lower().endswith(('.log', '.npz', '.pt', '.pth', '.ckpt')) for name in names):
            raise SystemExit("Release ZIP unexpectedly contains runtime logs or generated data/weights")

    print(f"Created {OUTPUT}")
    print(f"Files: {len(files)}; bytes: {OUTPUT.stat().st_size}; ZIP integrity: PASS")


if __name__ == "__main__":
    main()
