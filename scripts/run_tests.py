#!/usr/bin/env python3
"""Run each evaluation test directory in its own Python process.

Several skills intentionally use identically named modules such as
``test_validator.py``. Process isolation prevents module-cache collisions while
keeping the test command simple for local and CI use.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"


def test_directories(pattern: str) -> list[Path]:
    return sorted({path.parent for path in EVALS.rglob(pattern)})


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all isolated SEO-suite evaluation test directories.")
    parser.add_argument("--pattern", default="test_*.py", help="test file glob, default: test_*.py")
    args = parser.parse_args()
    directories = test_directories(args.pattern)
    if not directories:
        print("ERROR: no evaluation tests found", file=sys.stderr)
        return 1
    failures: list[str] = []
    for directory in directories:
        relative = directory.relative_to(ROOT).as_posix()
        print(f"\n== {relative} ==", flush=True)
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(directory), "-p", args.pattern, "-v"],
            cwd=ROOT,
            check=False,
        )
        if completed.returncode != 0:
            failures.append(relative)
    if failures:
        print("FAILED: " + ", ".join(failures), file=sys.stderr)
        return 1
    print(f"PASS: {len(directories)} isolated evaluation test directory/directories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
