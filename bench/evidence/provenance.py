"""Capture environment and source provenance for evidence manifests."""

from __future__ import annotations

import hashlib
import platform as platform_module
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from bench.evidence.schema import EvidenceManifest, RunBudget, utc_timestamp


class ProvenanceError(RuntimeError):
    """Raised when required provenance cannot be captured reliably."""


@dataclass(frozen=True, slots=True)
class GitState:
    revision: str
    dirty: bool


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def capture_git_state(repo_root: Path | str) -> GitState:
    """Capture HEAD and tracked/untracked dirtiness from a Git worktree."""
    root = Path(repo_root).resolve()

    def run(*arguments: str) -> str:
        try:
            process = subprocess.run(
                ["git", "-C", str(root), *arguments],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = ""
            if isinstance(exc, subprocess.CalledProcessError):
                detail = exc.stderr.strip()
            raise ProvenanceError(
                f"cannot capture Git provenance for {root}: {detail or exc}"
            ) from exc
        return process.stdout.strip()

    revision = run("rev-parse", "--verify", "HEAD").lower()
    status = run("status", "--porcelain=v1", "--untracked-files=normal")
    return GitState(revision=revision, dirty=bool(status))


def _portable_input_name(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root.resolve())
    except ValueError:
        # Evidence must not contain a machine-specific absolute path.
        return path.name
    return relative.as_posix()


def capture_manifest(
    *,
    repo_root: Path | str,
    input_path: Path | str,
    matrix_hash: str,
    matrix_unit: str,
    solver_name: str,
    solver_config: Mapping[str, Any] | None = None,
    budget: RunBudget | None = None,
    seed: int | None = None,
    created_at_utc: str | None = None,
) -> EvidenceManifest:
    """Build a complete manifest from the current repository and runtime."""
    root = Path(repo_root).resolve()
    source = Path(input_path)
    if not source.is_file():
        raise FileNotFoundError(f"evidence input does not exist: {source}")
    git = capture_git_state(root)
    return EvidenceManifest.create(
        created_at_utc=created_at_utc or utc_timestamp(),
        git_revision=git.revision,
        git_dirty=git.dirty,
        python_version=platform_module.python_version(),
        platform=platform_module.platform(),
        input_name=_portable_input_name(source, root),
        input_sha256=sha256_file(source),
        matrix_hash=matrix_hash,
        matrix_unit=matrix_unit,
        solver_name=solver_name,
        solver_config=solver_config,
        budget=budget,
        seed=seed,
    )
