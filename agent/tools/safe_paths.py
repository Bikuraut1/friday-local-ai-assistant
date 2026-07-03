from __future__ import annotations

import os
from pathlib import Path


FRIDAY_ROOT = Path(os.environ.get("FRIDAY_ROOT", r"D:\Friday"))
USER_HOME = Path(os.environ.get("USERPROFILE", str(Path.home())))

ALLOW_ROOTS = [
    FRIDAY_ROOT,
    USER_HOME / "Desktop",
    USER_HOME / "Documents",
    USER_HOME / "Downloads",
]

BLOCK_ROOTS = [
    Path(r"C:\Windows"),
    Path(r"C:\Windows\System32"),
    Path(r"C:\Boot"),
    Path(r"C:\EFI"),
    Path(r"C:\Recovery"),
]

BLOCK_FILES = {
    r"c:\boot.ini",
    r"c:\bootmgr",
    r"c:\hiberfil.sys",
    r"c:\pagefile.sys",
    r"c:\swapfile.sys",
}

REGISTRY_PREFIXES = (
    "hklm:",
    "hkcu:",
    "hkcr:",
    "hku:",
    "hkcc:",
    "registry::",
)


class SafetyError(ValueError):
    pass


def _norm(path: str | Path) -> Path:
    raw = str(path).strip().strip('"')
    if not raw:
        raise SafetyError("Empty path is not allowed.")
    if raw.lower().startswith(REGISTRY_PREFIXES):
        raise SafetyError("Registry paths are blocked.")
    return Path(raw).expanduser().resolve(strict=False)


def _is_under(path: Path, root: Path) -> bool:
    path_s = str(path).casefold()
    root_s = str(root.resolve(strict=False)).rstrip("\\/").casefold()
    return path_s == root_s or path_s.startswith(root_s + "\\")


def require_allowed_path(path: str | Path, *, must_exist: bool = False) -> Path:
    candidate = _norm(path)
    candidate_s = str(candidate).casefold()

    if candidate_s in BLOCK_FILES:
        raise SafetyError(f"Blocked system file: {candidate}")

    for root in BLOCK_ROOTS:
        if _is_under(candidate, root):
            raise SafetyError(f"Blocked system path: {candidate}")

    if not any(_is_under(candidate, root) for root in ALLOW_ROOTS):
        allowed = ", ".join(str(root) for root in ALLOW_ROOTS)
        raise SafetyError(f"Path is outside allowed roots: {candidate}. Allowed roots: {allowed}")

    if must_exist and not candidate.exists():
        raise SafetyError(f"Path does not exist: {candidate}")

    return candidate


def allowed_roots() -> list[str]:
    return [str(root.resolve(strict=False)) for root in ALLOW_ROOTS]


def blocked_roots() -> list[str]:
    return [str(root.resolve(strict=False)) for root in BLOCK_ROOTS]
