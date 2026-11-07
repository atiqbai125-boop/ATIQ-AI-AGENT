import os, zipfile, shutil, tempfile
from pathlib import Path, PurePosixPath
from core.config import WORK_DIR, MAX_FILES, MAX_UNPACKED_MB

ALLOWED_TEXT = {
    ".py",".html",".htm",".css",".js",".ts",".jsx",".tsx",".json",".xml",".yaml",".yml",
    ".md",".txt",".java",".kt",".gradle",".properties",".sql",".sh",".toml",".ini",".php",
    ".go",".rs",".c",".cpp",".h",".hpp",".swift",".dart",".vue",".svelte"
}
SKIP_DIRS = {".git",".gradle","node_modules","venv",".venv","__pycache__","build","dist"}

def safe_name(name: str) -> str:
    p = PurePosixPath(name.replace("\\", "/"))
    if p.is_absolute() or not p.parts or any(x in ("..", "") for x in p.parts):
        raise ValueError("Unsafe file path")
    return str(p)

def extract_zip(zip_path: Path, target: Path):
    total = 0
    count = 0
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = safe_name(info.filename)
            # Skip hidden metadata/cache folders commonly found in Android and Git projects.
            if any(part.startswith(".") for part in PurePosixPath(name).parts):
                continue
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("ZIP symlinks are not accepted")
            count += 1
            total += info.file_size
            if count > MAX_FILES or total > MAX_UNPACKED_MB * 1024 * 1024:
                raise ValueError("ZIP project exceeds configured safety limits")
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)

def inventory(folder: Path):
    rows = []
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(folder)
        if any(p in SKIP_DIRS or p.startswith(".") for p in rel.parts):
            continue
        rows.append(rel.as_posix())
        if len(rows) >= MAX_FILES:
            break
    return rows

def read_project_context(folder: Path, max_chars=45000):
    lines, used = [], 0
    for rel in inventory(folder):
        p = folder / rel
        if p.suffix.lower() not in ALLOWED_TEXT:
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        block = f"\n--- FILE: {rel} ---\n{content}\n"
        if used + len(block) > max_chars:
            break
        lines.append(block)
        used += len(block)
    return "\n".join(lines)

def apply_operations(folder: Path, operations):
    changed = []
    if len(operations) > 25:
        raise ValueError("একবারে সর্বোচ্চ ২৫টি ফাইল পরিবর্তন করা যাবে")
    for op in operations:
        if not isinstance(op, dict) or op.get("action") != "write":
            continue
        rel = safe_name(str(op.get("path", "")))
        if any(part.startswith(".") for part in PurePosixPath(rel).parts):
            raise ValueError("Hidden paths cannot be modified")
        path = folder / rel
        if path.suffix.lower() not in ALLOWED_TEXT:
            raise ValueError(f"Unsupported text file type: {rel}")
        content = op.get("content")
        if not isinstance(content, str) or len(content.encode("utf-8")) > 500_000:
            raise ValueError(f"Invalid or oversized content: {rel}")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            backup = path.with_suffix(path.suffix + ".atiq-backup")
            shutil.copy2(path, backup)
        path.write_text(content, encoding="utf-8")
        changed.append(rel)
    return changed

def make_zip(folder: Path, output: Path):
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in inventory(folder):
            zf.write(folder / rel, rel)
