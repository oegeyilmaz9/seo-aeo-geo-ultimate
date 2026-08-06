"""Shared safety checks for file-backed SEO artifact bundles.

Artifact validators accept paths supplied by users and may recurse into other
artifact validators. These helpers keep every declared reference inside a
regular, non-reparse-point bundle tree before it is read or hashed.
"""

from __future__ import annotations

import re
import stat
from pathlib import Path, PurePosixPath


def is_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    is_junction = getattr(path, "is_junction", None)
    return (
        path.is_symlink()
        or (callable(is_junction) and is_junction())
        or bool(getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    )


def ensure_safe_bundle(bundle: Path, errors: list[str]) -> bool:
    if not bundle.is_dir():
        errors.append("--bundle must resolve to a directory")
        return False
    if is_reparse(bundle):
        errors.append("--bundle must not be a symlink or reparse point")
        return False
    return True


def relative_path(value: object, field: str, errors: list[str]) -> PurePosixPath | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{field} must be a non-empty bundle-relative path")
        return None
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or normalized.startswith("//") or ".." in path.parts or re.match(r"^[A-Za-z]:", value):
        errors.append(f"{field} must be bundle-relative")
        return None
    return path


def resolve_relative(bundle: Path, value: object, field: str, errors: list[str]) -> Path | None:
    if not ensure_safe_bundle(bundle, errors):
        return None
    relative = relative_path(value, field, errors)
    if relative is None:
        return None
    candidate = bundle.joinpath(*relative.parts)
    try:
        candidate.resolve().relative_to(bundle.resolve())
    except ValueError:
        errors.append(f"{field} escapes bundle root")
        return None
    current = bundle
    for part in relative.parts:
        current /= part
        try:
            current.lstat()
        except OSError:
            break
        if is_reparse(current):
            errors.append(f"{field} must not traverse a symlink or reparse point")
            return None
    return candidate


def resolve_artifact_in_bundle(path: Path, bundle: Path, errors: list[str]) -> Path | None:
    if not ensure_safe_bundle(bundle, errors):
        return None
    try:
        relative = path.absolute().relative_to(bundle.absolute())
    except ValueError:
        errors.append("artifact must be inside --bundle")
        return None
    artifact = resolve_relative(bundle, relative.as_posix(), "artifact", errors)
    if artifact is not None and not artifact.is_file():
        errors.append("artifact must resolve to a regular file")
    return artifact
