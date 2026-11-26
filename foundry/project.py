"""Project creation and trusted, project-local extension loading."""
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from . import __version__

ROOT = Path(__file__).resolve().parent.parent
CORE = ("foundry", "docs", ".agents", ".codex", "AGENTS.md", "pyproject.toml",
        ".python-version", "uv.lock", ".gitignore")
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")


def copy_item(source, target):
    if source.is_dir():
        shutil.copytree(source, target, ignore=IGNORE)
    else:
        shutil.copyfile(source, target)


def initialize(target, example=False):
    template = ROOT / "templates" / "project"
    if not template.is_dir():
        raise ValueError("请从发行包根目录运行 init")
    target.mkdir(parents=True, exist_ok=False)
    try:
        for name in CORE:
            copy_item(ROOT / name, target / name)
        for item in template.iterdir():
            copy_item(item, target / item.name)
        if example:
            sample = ROOT / "examples" / "dispatch"
            for item in sample.iterdir():
                if item.is_dir():
                    shutil.copytree(item, target / item.name, dirs_exist_ok=True, ignore=IGNORE)
                else:
                    shutil.copyfile(item, target / item.name)
        manifest = {"version": __version__, "contract": 1, "files": managed_files(target)}
        (target / "foundry-release.json").write_text(json.dumps(manifest, indent=2))
    except BaseException:
        shutil.rmtree(target)
        raise
    return target.resolve()


def extension(path):
    """The developer controls the Python modules in a trusted project."""
    key = "_foundry_" + hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(key, path, submodule_search_locations=[str(path.parent)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module


def digest_files(root, paths):
    hasher = hashlib.sha256()
    for path in sorted(paths):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            relative = path.relative_to(root).as_posix().encode()
            hasher.update(len(relative).to_bytes(4, "big") + relative)
            hasher.update(hashlib.sha256(path.read_bytes()).digest())
    return hasher.hexdigest()


def managed_files(root):
    result = {}
    for item in CORE:
        path = root / item
        for file in path.rglob("*") if path.is_dir() else [path]:
            if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc":
                result[file.relative_to(root).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    return result


def upgrade(source, destination):
    """Side-by-side upgrade of the supported single-project layout."""
    source = source.resolve()
    destination = destination.resolve()
    if destination.is_relative_to(source):
        raise ValueError("升级候选必须位于旧项目之外的新目录")
    manifest = json.loads((source / "foundry-release.json").read_text())
    if manifest.get("contract") != 1 or manifest.get("files") != managed_files(source):
        raise ValueError("框架文件已被定制或业务契约版本不兼容，请先审阅差异")
    owned = {"business", "evals", "SPEC.md", "CHECKLIST.md", "README.md"}
    kept_in_source = {".git", ".runs", ".venv", "__pycache__", ".env", "foundry-release.json"}
    extra = {p.name for p in source.iterdir() if not p.name.startswith(".env.")} - owned - kept_in_source - set(CORE)
    if extra:
        raise ValueError("请先明确这些额外资产的迁移方式：" + ", ".join(sorted(extra)))
    for name in owned:
        path = source / name
        if not path.exists() or any(p.is_symlink() for p in [path, *path.rglob("*")]):
            raise ValueError(f"缺少业务资产或含外部符号链接：{name}")
    initialize(destination)
    try:
        for name in owned:
            path = destination / name
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            copy_item(source / name, path)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return destination
